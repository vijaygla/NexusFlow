import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WorkflowService } from '../../core/services/workflow.service';
import { ChatPanelComponent } from '../chat-panel/chat-panel.component';
import { CodeViewerComponent } from '../code-viewer/code-viewer.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, ChatPanelComponent, CodeViewerComponent],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent {
  readonly workflow = inject(WorkflowService);

  readonly stepperSteps = [
    { id: 'init', label: 'User Specification', icon: '📝' },
    { id: 'coder', label: 'Coder Agent Loop', icon: '🤖' },
    { id: 'sandbox', label: 'Subprocess Sandbox', icon: '⚡' },
    { id: 'reviewer', label: 'Reviewer Agent Audit', icon: '🔍' },
    { id: 'complete', label: 'Production Ready', icon: '🚀' },
  ];

  isStepActive(stepId: string): boolean {
    const current = this.workflow.currentNode();
    if (stepId === 'sandbox') {
      return current === 'coder' && !!this.workflow.executionResult();
    }
    return current === stepId;
  }

  isStepPassed(stepId: string): boolean {
    const current = this.workflow.currentNode();
    if (current === 'complete') return true;
    if (stepId === 'init') return current !== 'idle';
    if (stepId === 'coder') return this.workflow.iterations() > 0;
    if (stepId === 'sandbox') return !!this.workflow.executionResult()?.success;
    if (stepId === 'reviewer') return current === 'complete' || (this.workflow.iterations() > 1);
    return false;
  }

  openHistory(): void {
    this.workflow.toggleHistoryDrawer();
  }

  loadSession(sessionId: string): void {
    this.workflow.loadHistoricalSession(sessionId);
  }
}
