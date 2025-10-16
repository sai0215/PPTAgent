<template>
  <div class="generate-container">
    <p class="task-id">Task ID: {{ taskId }}</p>
    <progress :value="progress" max="100" class="progress-bar"></progress>
    <p class="status-message">{{ statusMessage }}</p>
    <a v-if="downloadLink" :href="downloadLink" :download="filename" class="download-link">Download PPTX</a>
    <input v-model="feedback" placeholder="Enter your feedback with contact information" class="feedback-input" />
    <button @click="submitFeedback" class="feedback-button">Submit Feedback</button>
  </div>
</template>

<script>
export default {
  name: 'GenerateComponent',
  data() {
    return {
      progress: 0,
      statusMessage: 'Starting...',
      downloadLink: '',
      taskId: history.state.taskId,
      feedback: '',
      filename: 'final.pptx',
      socket: null,
    }
  },
  created() {
    this.startGeneration()
  },
  beforeUnmount() {
    this.closeSocket()
  },
  methods: {
    async startGeneration() {
      console.log("Connecting to websocket", `/wsapi/${this.taskId}`)
      this.socket = new WebSocket(`/wsapi/${this.taskId}`)

      this.socket.onmessage = (event) => {
        console.log("Socket Received message:", event.data)
        const data = JSON.parse(event.data)
        this.progress = data.progress
        this.statusMessage = data.status
        if (data.progress >= 100) {
          this.closeSocket()
          this.fetchDownloadLink()
        }
      }
      this.socket.onerror = (error) => {
        console.error("WebSocket error:", error)
        this.statusMessage = 'WebSocket connection failed.'
        this.closeSocket()
      }
    },
    async fetchDownloadLink() {
      try {
        const downloadResponse = await this.$axios.get('/api/download', { params: { task_id: this.taskId }, responseType: 'blob' })
        this.downloadLink = URL.createObjectURL(downloadResponse.data)
        this.filename = "ppagent_" + this.taskId.replace('/', '_') + '.pptx'
      } catch (error) {
        console.error("Download error:", error)
        this.statusMessage += '\nFailed to continue the task.'
      }
    },
    async submitFeedback() {
      if (!this.feedback) {
        alert('Please enter your feedback with contact information.')
        return
      }
      try {
        await this.$axios.post('/api/feedback', { feedback: this.feedback, task_id: this.taskId })
        this.statusMessage = 'Feedback submitted successfully.'
        this.feedback = ''
      } catch (error) {
        console.error("Feedback submission error:", error)
        this.statusMessage = 'Failed to submit feedback.'
      }
    },
    closeSocket() {
      if (this.socket) {
        this.socket.close()
        this.socket = null
      }
    }
  }
}
</script>

<style scoped>
.generate-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem 2rem;
  max-width: 800px;
  margin: 0 auto;
  background: linear-gradient(135deg, #FFFFFF 0%, #FFF9F5 100%);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(232, 119, 34, 0.12);
  border: 1px solid rgba(232, 119, 34, 0.1);
}

.task-id {
  font-size: 1rem;
  margin-bottom: 2rem;
  color: #D04A02;
  font-weight: 600;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, #FFE4D1 0%, #FFF5EE 100%);
  border-left: 4px solid #E87722;
  border-radius: 8px;
  width: 100%;
  box-sizing: border-box;
  box-shadow: 0 2px 8px rgba(232, 119, 34, 0.15);
}

.progress-bar {
  width: 100%;
  height: 36px;
  margin-bottom: 1.5rem;
  appearance: none;
  background: linear-gradient(135deg, #FFF9F5 0%, #FFE8D6 100%);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: inset 0 2px 8px rgba(232, 119, 34, 0.1);
  border: 2px solid rgba(232, 119, 34, 0.2);
}

.progress-bar::-webkit-progress-bar {
  background: linear-gradient(135deg, #FFF9F5 0%, #FFE8D6 100%);
  border-radius: 18px;
}

.progress-bar::-webkit-progress-value {
  background: linear-gradient(90deg, #E87722 0%, #FFB85C 50%, #E87722 100%);
  border-radius: 18px;
  transition: width 0.3s ease;
  box-shadow: 0 2px 8px rgba(232, 119, 34, 0.4);
}

.progress-bar::-moz-progress-bar {
  background: linear-gradient(90deg, #E87722 0%, #FFB85C 50%, #E87722 100%);
  border-radius: 18px;
}

.status-message {
  font-size: 1.125rem;
  margin-bottom: 2rem;
  color: #D04A02;
  font-weight: 500;
  text-align: center;
  line-height: 1.6;
}

.download-link {
  font-size: 1.125rem;
  color: white;
  background: linear-gradient(135deg, #E87722 0%, #D04A02 100%);
  text-decoration: none;
  padding: 1rem 2.5rem;
  border-radius: 12px;
  transition: all 0.3s ease;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(232, 119, 34, 0.3);
  margin-bottom: 2rem;
}

.download-link:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 24px rgba(232, 119, 34, 0.4);
  background: linear-gradient(135deg, #F08030 0%, #E05510 100%);
}

.feedback-input {
  margin-top: 2rem;
  padding: 1rem;
  width: 100%;
  box-sizing: border-box;
  border: 2px solid rgba(232, 119, 34, 0.3);
  border-radius: 12px;
  font-size: 1rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  transition: all 0.3s ease;
  min-height: 100px;
  resize: vertical;
  background: linear-gradient(135deg, #FFFFFF 0%, #FFF9F5 100%);
  color: #D04A02;
}

.feedback-input::placeholder {
  color: rgba(208, 74, 2, 0.5);
}

.feedback-input:focus {
  outline: none;
  border-color: #E87722;
  box-shadow: 0 0 0 4px rgba(232, 119, 34, 0.15);
  background: white;
}

.feedback-button {
  margin-top: 1rem;
  padding: 0.875rem 2rem;
  background: linear-gradient(135deg, #FFE4D1 0%, #FFD4B8 100%);
  color: #D04A02;
  border: 2px solid rgba(232, 119, 34, 0.3);
  border-radius: 12px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(232, 119, 34, 0.2);
}

.feedback-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(232, 119, 34, 0.3);
  background: linear-gradient(135deg, #FFD4B8 0%, #FFC49F 100%);
  border-color: #E87722;
}

.feedback-button:active {
  transform: translateY(0);
}

@media (max-width: 768px) {
  .generate-container {
    padding: 2rem 1rem;
  }
  
  .download-link {
    width: 100%;
    text-align: center;
  }
}
</style>
