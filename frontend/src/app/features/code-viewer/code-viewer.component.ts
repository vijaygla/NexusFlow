import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WorkflowService } from '../../core/services/workflow.service';

@Component({
  selector: 'app-code-viewer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './code-viewer.component.html',
  styleUrls: ['./code-viewer.component.scss'],
})
export class CodeViewerComponent {
  readonly workflow = inject(WorkflowService);
  readonly copied = signal<boolean>(false);
  readonly activeTab = signal<'code' | 'review' | 'sandbox' | 'security'>('code');

  readonly fileNames = computed<string[]>(() => {
    const iter = this.workflow.selectedIteration();
    const history = this.workflow.iterationHistory();
    if (iter > 0 && history.length >= iter) {
      return Object.keys(history[iter - 1]?.files || {});
    }
    return Object.keys(this.workflow.generatedFiles());
  });

  readonly codeLines = computed<string[]>(() => {
    const code = this.workflow.activeFileContent();
    return code ? code.split('\n') : ['# Awaiting synthesized code from Coder Agent...'];
  });

  selectFile(name: string): void {
    this.workflow.selectFile(name);
  }

  setIteration(iter: number): void {
    this.workflow.setIterationView(iter);
  }

  toggleDiff(): void {
    this.workflow.toggleDiffMode();
  }

  async copyCurrentCode(): Promise<void> {
    const code = this.workflow.activeFileContent();
    if (!code) return;
    await navigator.clipboard.writeText(code);
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }

  downloadCurrentFile(): void {
    const code = this.workflow.activeFileContent();
    const name = this.workflow.activeFileName();
    if (!code) return;

    const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }
}
