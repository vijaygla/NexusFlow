import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WorkflowService } from '../../core/services/workflow.service';

@Component({
  selector: 'app-chat-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-panel.component.html',
  styleUrls: ['./chat-panel.component.scss'],
})
export class ChatPanelComponent {
  readonly workflow = inject(WorkflowService);
  userPrompt = '';
  speechRecognition: any = null;

  readonly quickPrompts = [
    'Create an enterprise LRU Cache with TTL expiry, thread-safety, and test suite.',
    'Build a Binary Search Tree with insert, delete, in-order traversal, and unit tests.',
    'Implement a Rate Limiter using Token Bucket algorithm with complete test suite.',
    'Build an asynchronous Event Bus with subscribe, publish, and replay buffers.',
  ];

  selectQuickPrompt(prompt: string): void {
    this.userPrompt = prompt;
  }

  submitPrompt(): void {
    if (!this.userPrompt.trim() || this.workflow.isStreaming()) return;
    const promptToSend = this.userPrompt.trim();
    this.userPrompt = '';
    this.workflow.startWorkflow(promptToSend);
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.submitPrompt();
    }
  }

  toggleSpeechRecognition(): void {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech Recognition is not supported by your current browser.');
      return;
    }

    if (this.workflow.isListeningSpeech()) {
      if (this.speechRecognition) {
        this.speechRecognition.stop();
      }
      this.workflow.isListeningSpeech.set(false);
      return;
    }

    try {
      this.speechRecognition = new SpeechRecognition();
      this.speechRecognition.continuous = true;
      this.speechRecognition.interimResults = true;
      this.speechRecognition.lang = 'en-US';

      this.speechRecognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript) {
          this.userPrompt = (this.userPrompt ? this.userPrompt + ' ' : '') + transcript;
        }
      };

      this.speechRecognition.onerror = (err: any) => {
        console.warn('Speech recognition error:', err);
        this.workflow.isListeningSpeech.set(false);
      };

      this.speechRecognition.onend = () => {
        this.workflow.isListeningSpeech.set(false);
      };

      this.speechRecognition.start();
      this.workflow.isListeningSpeech.set(true);
    } catch (e) {
      console.error('Failed to start speech recognition:', e);
      this.workflow.isListeningSpeech.set(false);
    }
  }
}
