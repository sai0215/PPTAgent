import asyncio
import hashlib
import json
import os
import sys
import traceback
import uuid
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime
from os.path import join

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from pptagent.document import Document
from pptagent.induct import SlideInducter
from pptagent.model_utils import ModelManager, parse_pdf
from pptagent.multimodal import ImageLabler
from pptagent.pptgen import PPTAgent
from pptagent.pptx_parser import parse_standard_template_pptx, content_to_document_format
from pptagent.presentation import Presentation
from pptagent.utils import Config, get_logger, package_join, ppt_to_images_async

# constants
DEBUG = True if len(sys.argv) == 1 else False
RUNS_DIR = package_join("runs")
STAGES = [
    "Designer Template Parsing",
    "Standard Template Parsing",
    "Content Analysis",
    "PPT Generation",
    "Success!",
]


models = ModelManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    assert await models.test_connections(), "Model connection test failed"
    yield


# server
logger = get_logger(__name__)
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
progress_store: dict[str, dict] = {}
active_connections: dict[str, WebSocket] = {}


class ProgressManager:
    def __init__(self, task_id: str, stages: list[str], debug: bool = True):
        self.task_id = task_id
        self.stages = stages
        self.debug = debug
        self.failed = False
        self.current_stage = 0
        self.total_stages = len(stages)

    async def report_progress(self):
        assert self.task_id in active_connections, (
            "WebSocket connection is already closed"
        )
        self.current_stage += 1
        progress = int((self.current_stage / self.total_stages) * 100)
        await send_progress(
            active_connections[self.task_id],
            f"Stage: {self.stages[self.current_stage - 1]}",
            progress,
        )

    async def fail_stage(self, error_message: str):
        await send_progress(
            active_connections[self.task_id],
            f"{self.stages[self.current_stage]} Error: {error_message}",
            100,
        )
        self.failed = True
        active_connections.pop(self.task_id, None)
        if self.debug:
            logger.error(
                f"{self.task_id}: {self.stages[self.current_stage]} Error: {error_message}"
            )


@app.post("/api/upload")
async def create_task(
    designerTemplate: UploadFile = File(None),  # Previously pptxFile
    standardTemplate: UploadFile = File(None),  # Previously pdfFile, now also PPTX
    topic: str = Form(None),
    numberOfPages: int = Form(...),
):
    task_id = datetime.now().strftime("20%y-%m-%d") + "/" + str(uuid.uuid4())
    logger.info(f"task created: {task_id}")
    os.makedirs(join(RUNS_DIR, task_id))
    task = {
        "numberOfPages": numberOfPages,
        "designer_template": "default_template",
    }
    
    # Handle Designer Template (style/layout reference)
    if designerTemplate is not None:
        designer_blob = await designerTemplate.read()
        designer_md5 = hashlib.md5(designer_blob).hexdigest()
        task["designer_template"] = designer_md5
        designer_dir = join(RUNS_DIR, "designer", designer_md5)
        if not os.path.exists(designer_dir):
            os.makedirs(designer_dir, exist_ok=True)
            with open(join(designer_dir, "source.pptx"), "wb") as f:
                f.write(designer_blob)
        logger.info(f"Designer Template uploaded: {designerTemplate.filename}")
    
    # Handle Standard Template (content source - now PPTX)
    if standardTemplate is not None:
        standard_blob = await standardTemplate.read()
        standard_md5 = hashlib.md5(standard_blob).hexdigest()
        task["standard_template"] = standard_md5
        standard_dir = join(RUNS_DIR, "standard", standard_md5)
        if not os.path.exists(standard_dir):
            os.makedirs(standard_dir, exist_ok=True)
            # Save as PPTX (not PDF anymore)
            with open(join(standard_dir, "source.pptx"), "wb") as f:
                f.write(standard_blob)
        logger.info(f"Standard Template uploaded: {standardTemplate.filename}")
    elif topic is not None:
        task["topic"] = topic
    
    progress_store[task_id] = task
    # Start the PPT generation task asynchronously
    asyncio.create_task(ppt_gen(task_id))
    return {"task_id": task_id.replace("/", "|")}


async def send_progress(websocket: WebSocket | None, status: str, progress: int):
    if websocket is None:
        logger.info(f"websocket is None, status: {status}, progress: {progress}")
        return
    await websocket.send_json({"progress": progress, "status": status})


@app.websocket("/wsapi/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    task_id = task_id.replace("|", "/")
    if task_id in progress_store:
        await websocket.accept()
    else:
        raise HTTPException(status_code=404, detail="Task not found")
    active_connections[task_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket disconnected: %s", task_id)
        active_connections.pop(task_id, None)


@app.get("/api/download")
async def download(task_id: str):
    task_id = task_id.replace("|", "/")
    if not os.path.exists(join(RUNS_DIR, task_id)):
        raise HTTPException(status_code=404, detail="Task not created yet")
    file_path = join(RUNS_DIR, task_id, "final.pptx")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/pptx",
            headers={"Content-Disposition": "attachment; filename=pptagent.pptx"},
        )
    raise HTTPException(status_code=404, detail="Task not finished yet")


@app.post("/api/feedback")
async def feedback(request: Request):
    body = await request.json()
    feedback = body.get("feedback")
    task_id = body.get("task_id")

    with open(join(RUNS_DIR, "feedback", f"{task_id}.txt"), "w", encoding="utf-8") as f:
        f.write(feedback)
    return {"message": "Feedback submitted successfully"}


@app.get("/")
async def hello():
    return {"message": "Hello, World!"}


async def ppt_gen(task_id: str, rerun=False):
    if rerun:
        task_id = task_id.replace("|", "/")
        active_connections[task_id] = None
        progress_store[task_id] = json.load(
            open(join(RUNS_DIR, task_id, "task.json"), encoding="utf-8")
        )

    # Wait for WebSocket connection
    for _ in range(100):
        if task_id in active_connections:
            break
        await asyncio.sleep(0.02)
    else:
        progress_store.pop(task_id)
        return

    task = progress_store.pop(task_id)
    designer_md5 = task["designer_template"]
    standard_md5 = task["standard_template"]
    generation_config = Config(join(RUNS_DIR, task_id))
    designer_config = Config(join(RUNS_DIR, "designer", designer_md5))
    json.dump(
        task, open(join(generation_config.RUN_DIR, "task.json"), "w", encoding="utf-8")
    )
    progress = ProgressManager(task_id, STAGES)
    parsed_standard_dir = join(RUNS_DIR, "standard", standard_md5)
    ppt_image_folder = join(designer_config.RUN_DIR, "slide_images")

    await send_progress(
        active_connections[task_id], "task initialized successfully", 10
    )

    try:
        # Designer Template parsing (style/layout reference)
        logger.info(f"{task_id}: Parsing Designer Template")
        presentation = Presentation.from_file(
            join(designer_config.RUN_DIR, "source.pptx"), designer_config
        )
        if not os.path.exists(ppt_image_folder) or len(
            os.listdir(ppt_image_folder)
        ) != len(presentation):
            await ppt_to_images_async(
                join(designer_config.RUN_DIR, "source.pptx"), ppt_image_folder
            )
            assert len(os.listdir(ppt_image_folder)) == len(presentation) + len(
                presentation.error_history
            ), "Number of parsed slides and images do not match"

            for err_idx, _ in presentation.error_history:
                os.remove(join(ppt_image_folder, f"slide_{err_idx:04d}.jpg"))
            for i, slide in enumerate(presentation.slides, 1):
                slide.slide_idx = i
                os.rename(
                    join(ppt_image_folder, f"slide_{slide.real_idx:04d}.jpg"),
                    join(ppt_image_folder, f"slide_{slide.slide_idx:04d}.jpg"),
                )

        labler = ImageLabler(presentation, designer_config)
        if os.path.exists(join(designer_config.RUN_DIR, "image_stats.json")):
            image_stats = json.load(
                open(join(designer_config.RUN_DIR, "image_stats.json"), encoding="utf-8")
            )
            labler.apply_stats(image_stats)
        else:
            await labler.caption_images_async(models.vision_model)
            json.dump(
                labler.image_stats,
                open(
                    join(designer_config.RUN_DIR, "image_stats.json"),
                    "w",
                    encoding="utf-8",
                ),
                ensure_ascii=False,
                indent=4,
            )
        await progress.report_progress()

        # Standard Template parsing (content source with fonts)
        logger.info(f"{task_id}: Parsing Standard Template PPTX")
        if not os.path.exists(join(parsed_standard_dir, "content.json")):
            # Parse Standard Template PPTX with font information
            pptx_content = await parse_standard_template_pptx(
                join(RUNS_DIR, "standard", standard_md5, "source.pptx"),
                parsed_standard_dir,
            )
            
            # Convert to markdown for compatibility
            markdown_content = pptx_content.to_markdown()
            with open(join(parsed_standard_dir, "source.md"), "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            # Save structured content with font information
            content_dict = content_to_document_format(pptx_content)
            json.dump(
                content_dict,
                open(join(parsed_standard_dir, "content.json"), "w"),
                ensure_ascii=False,
                indent=4,
            )
            logger.info(f"{task_id}: Parsed {pptx_content.num_slides} slides from Standard Template")
        else:
            content_dict = json.load(
                open(join(parsed_standard_dir, "content.json"), encoding="utf-8")
            )
            markdown_content = open(
                join(parsed_standard_dir, "source.md"), encoding="utf-8"
            ).read()
            logger.info(f"{task_id}: Loaded cached Standard Template content")
        
        await progress.report_progress()

        # Content Analysis - Convert to Document format
        logger.info(f"{task_id}: Analyzing content structure")
        if not os.path.exists(join(parsed_standard_dir, "refined_doc.json")):
            source_doc = await Document.from_markdown(
                markdown_content,
                models.language_model,
                models.vision_model,
                parsed_standard_dir,
            )
            # Enhance with font information from content_dict
            source_doc_dict = source_doc.model_dump()
            source_doc_dict["font_metadata"] = content_dict  # Store font info
            
            json.dump(
                source_doc_dict,
                open(join(parsed_standard_dir, "refined_doc.json"), "w"),
                ensure_ascii=False,
                indent=4,
            )
        else:
            source_doc_dict = json.load(
                open(join(parsed_standard_dir, "refined_doc.json"), encoding="utf-8")
            )
            source_doc = Document.model_validate(source_doc_dict)
        await progress.report_progress()

        # Slide Induction (Designer Template analysis)
        logger.info(f"{task_id}: Analyzing Designer Template layouts")
        if not os.path.exists(join(designer_config.RUN_DIR, "slide_induction.json")):
            deepcopy(presentation).save(
                join(designer_config.RUN_DIR, "template.pptx"), layout_only=True
            )
            await ppt_to_images_async(
                join(designer_config.RUN_DIR, "template.pptx"),
                join(designer_config.RUN_DIR, "template_images"),
            )
            slide_inducter = SlideInducter(
                presentation,
                ppt_image_folder,
                join(designer_config.RUN_DIR, "template_images"),
                designer_config,
                models.image_model,
                models.language_model,
                models.vision_model,
            )
            layout_induction = await slide_inducter.layout_induct()
            slide_induction = await slide_inducter.content_induct(layout_induction)
            json.dump(
                slide_induction,
                open(
                    join(designer_config.RUN_DIR, "slide_induction.json"),
                    "w",
                    encoding="utf-8",
                ),
                ensure_ascii=False,
                indent=4,
            )
        else:
            slide_induction = json.load(
                open(
                    join(designer_config.RUN_DIR, "slide_induction.json"), encoding="utf-8"
                )
            )
        await progress.report_progress()

        # PPT Generation - Merge Standard Template content with Designer Template style
        logger.info(f"{task_id}: Generating presentation with Designer Template style and Standard Template content")
        ppt_agent = PPTAgent(
            models.language_model,
            models.vision_model,
            error_exit=False,
            retry_times=5,
        )
        ppt_agent.set_reference(
            slide_induction=slide_induction,
            presentation=presentation,
        )

        prs, _ = await ppt_agent.generate_pres(
            source_doc=source_doc,
            num_slides=task["numberOfPages"],
        )
        prs.save(join(generation_config.RUN_DIR, "final.pptx"))
        logger.info(f"{task_id}: Presentation generated successfully!")
        await progress.report_progress()
    except Exception as e:
        await progress.fail_stage(str(e))
        traceback.print_exc()


if __name__ == "__main__":
    import uvicorn

    ip = "0.0.0.0"
    uvicorn.run(app, host=ip, port=9297)
