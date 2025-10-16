<template>
  <!-- Upload form -->
  <div class="upload-container">
    <div class="upload-options">
      <!-- Row 1: Upload Buttons -->
      <div class="upload-buttons">
        <div class="upload-section">
          <label for="pptx-upload" class="upload-label">
            Upload PPTX
            <span v-if="pptxFile" class="uploaded-symbol">✔️</span>
          </label>
          <input type="file" id="pptx-upload" @change="handleFileUpload($event, 'pptx')" accept=".pptx" />
        </div>
        <div class="upload-section">
          <label for="pdf-upload" class="upload-label">
            Upload PDF
            <span v-if="pdfFile" class="uploaded-symbol">✔️</span>
          </label>
          <input type="file" id="pdf-upload" @change="handleFileUpload($event, 'pdf')" accept=".pdf" />
        </div>
      </div>

      <!-- Row 2: Selectors -->
      <div class="selectors">
        <div class="pages-selection">
          <label class="selector-label">Number of Slides</label>
          <select v-model="selectedPages">
            <option v-for="page in pagesOptions" :key="page" :value="page">{{ page }} slides</option>
          </select>
        </div>
      </div>

      <!-- Row 3: Button -->
      <button @click="goToGenerate" class="next-button">Next</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UploadComponent',
  data() {
    return {
      pptxFile: null,
      pdfFile: null,
      selectedPages: 6,
      pagesOptions: Array.from({ length: 12 }, (_, i) => i + 3),
      isPptxEnabled:true
    }
  },
  methods: {
    handleFileUpload(event, fileType) {
      console.log("file uploaded :", fileType)
      const file = event.target.files[0]
      if (fileType === 'pptx') {
        this.pptxFile = file
      } else if (fileType === 'pdf') {
        this.pdfFile = file
      }
    },
    async goToGenerate() {
      this.$axios.get('/')
        .then(response => {
          console.log("Backend is running", response.data);
        })
        .catch(error => {
          console.error(error);
          alert('Backend is not running or too busy, your task will not be processed');
          return;
        });

      if (!this.pdfFile) {
        alert('Please upload a PDF file.');
        return;
      }

      const formData = new FormData();
      if (this.pptxFile) {
        formData.append('pptxFile', this.pptxFile);
      }
      formData.append('pdfFile', this.pdfFile);
      formData.append('numberOfPages', this.selectedPages);

      try {
        const uploadResponse = await this.$axios.post('/api/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        const taskId = uploadResponse.data.task_id
        console.log("Task ID:", taskId)
        // Navigate to Generate component with taskId
        this.$router.push({ name: 'Generate', state: { taskId: taskId } })
      } catch (error) {
        console.error("Upload error:", error)
        this.statusMessage = 'Failed to upload files.'
      }
    }
  }
}
</script>

<style scoped>
.upload-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  background: linear-gradient(135deg, #FFFFFF 0%, #FFF9F5 100%);
  padding: 3rem 2rem;
  box-sizing: border-box;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(232, 119, 34, 0.12);
  border: 1px solid rgba(232, 119, 34, 0.1);
}

.upload-options {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
  width: 100%;
  max-width: 900px;
}

.upload-buttons,
.selectors {
  display: flex;
  justify-content: center;
  gap: 2rem;
  width: 100%;
}

.upload-section,
.pages-selection {
  flex: 1;
  max-width: 300px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.selector-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: #E87722;
  margin-bottom: 0.75rem;
  text-align: center;
}

.upload-label {
  position: relative;
  background: linear-gradient(135deg, #FFE4D1 0%, #FFD4B8 100%);
  color: #D04A02;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  cursor: pointer;
  width: 100%;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  font-size: 1rem;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(232, 119, 34, 0.2);
  border: 2px solid rgba(232, 119, 34, 0.3);
}

.upload-label:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 24px rgba(232, 119, 34, 0.3);
  background: linear-gradient(135deg, #FFD4B8 0%, #FFC49F 100%);
  border-color: #E87722;
}

.upload-section input[type="file"] {
  display: none;
}

.pages-selection select {
  padding: 0.875rem;
  border-radius: 12px;
  border: 2px solid rgba(232, 119, 34, 0.3);
  width: 100%;
  box-sizing: border-box;
  font-size: 1rem;
  color: #D04A02;
  background: linear-gradient(135deg, #FFFFFF 0%, #FFF9F5 100%);
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(232, 119, 34, 0.1);
}

.pages-selection select:hover {
  border-color: #E87722;
  box-shadow: 0 4px 16px rgba(232, 119, 34, 0.2);
  transform: translateY(-2px);
}

.pages-selection select:focus {
  outline: none;
  border-color: #E87722;
  box-shadow: 0 0 0 4px rgba(232, 119, 34, 0.15);
}

.next-button {
  background: linear-gradient(135deg, #E87722 0%, #D04A02 100%);
  color: white;
  padding: 1rem 3rem;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  width: 240px;
  display: block;
  margin: 2rem auto 0;
  font-size: 1.125rem;
  font-weight: 700;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(232, 119, 34, 0.3);
}

.next-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 24px rgba(232, 119, 34, 0.4);
  background: linear-gradient(135deg, #F08030 0%, #E05510 100%);
}

.next-button:active {
  transform: translateY(-1px);
}

.uploaded-symbol {
  position: absolute;
  right: 1rem;
  color: #4CAF50;
  font-size: 1.25rem;
  filter: drop-shadow(0 2px 4px rgba(76, 175, 80, 0.3));
}

@media (max-width: 768px) {
  .upload-buttons,
  .selectors {
    flex-direction: column;
    gap: 1.5rem;
  }

  .upload-section,
  .pages-selection {
    max-width: 100%;
  }

  .next-button {
    width: 100%;
  }
}

.or-divider {
  display: flex;
  align-items: center;
  color: #E87722;
  font-weight: 600;
  font-size: 0.875rem;
  margin: 0;
}

@media (max-width: 768px) {
  .or-divider {
    margin: 0;
    justify-content: center;
  }
}
</style>
