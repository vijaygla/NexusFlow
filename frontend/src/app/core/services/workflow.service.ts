import { Injectable, signal, computed } from '@angular/core';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'coder' | 'reviewer' | 'system';
  content: string;
  timestamp: Date;
  metadata?: any;
}

export interface ExecutionTelemetry {
  success: boolean;
  exit_code: number;
  stdout: string;
  stderr: string;
  execution_time_seconds?: number;
  language?: string;
}

export interface QualityScorecard {
  overallScore: number;
  testPassRate: number;
  codeQualityScore: number;
  securityScore: number;
  verdict: 'PASS' | 'NEEDS_REVISION' | 'PENDING';
}

export interface SecurityVulnerability {
  id: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  name: string;
  file: string;
  line: number;
  snippet: string;
  message: string;
  recommendation: string;
}

export interface SecurityReport {
  overall_score: number;
  verdict: 'CLEAN' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK';
  files_analyzed: number;
  total_vulnerabilities: number;
  vulnerabilities: SecurityVulnerability[];
}

export interface LanguageOption {
  id: string;
  name: string;
  ext: string;
}

@Injectable({
  providedIn: 'root',
})
export class WorkflowService {
  private readonly baseUrl = 'http://localhost:8000';

  // Universal Languages Catalog
  readonly availableLanguages: LanguageOption[] = [
    { id: 'python', name: 'Python 3.12', ext: 'py' },
    { id: 'typescript', name: 'TypeScript', ext: 'ts' },
    { id: 'javascript', name: 'JavaScript (Node.js)', ext: 'js' },
    { id: 'java', name: 'Java (JDK 25)', ext: 'java' },
    { id: 'csharp', name: 'C# (.NET)', ext: 'cs' },
    { id: 'cpp', name: 'C++', ext: 'cpp' },
    { id: 'c', name: 'C', ext: 'c' },
    { id: 'go', name: 'Go', ext: 'go' },
    { id: 'rust', name: 'Rust', ext: 'rs' },
    { id: 'sql', name: 'SQL (MS SQL Server)', ext: 'sql' },
    { id: 'ruby', name: 'Ruby', ext: 'rb' },
    { id: 'php', name: 'PHP', ext: 'php' },
    { id: 'kotlin', name: 'Kotlin', ext: 'kt' },
    { id: 'swift', name: 'Swift', ext: 'swift' },
    { id: 'scala', name: 'Scala', ext: 'scala' },
    { id: 'powershell', name: 'PowerShell', ext: 'ps1' },
    { id: 'bash', name: 'Bash / Shell', ext: 'sh' },
    { id: 'html', name: 'HTML / CSS / Web', ext: 'html' },
    { id: 'custom', name: 'Custom Language...', ext: 'txt' },
  ];

  // Core Reactive Signals
  readonly currentNode = signal<string>('idle');
  readonly isStreaming = signal<boolean>(false);
  readonly currentTokens = signal<string>('');
  readonly generatedFiles = signal<Record<string, string>>({});
  readonly activeFileName = signal<string>('main.py');
  readonly reviewFeedback = signal<string>('');
  readonly iterations = signal<number>(0);
  readonly executionResult = signal<ExecutionTelemetry | null>(null);
  readonly messages = signal<ChatMessage[]>([]);
  readonly backendHealth = signal<any>(null);

  // Universal Language Signals
  readonly targetLanguage = signal<string>('python');
  readonly customLanguageName = signal<string>('');
  readonly sandboxLanguage = signal<string>('python');

  // Next-Level Signals
  readonly iterationHistory = signal<Array<any>>([]);
  readonly selectedIteration = signal<number>(0); // 0 = Latest
  readonly diffMode = signal<boolean>(false);
  readonly securityReport = signal<SecurityReport | null>(null);
  readonly isRunningSecurity = signal<boolean>(false);
  readonly historyList = signal<Array<any>>([]);
  readonly analyticsMetrics = signal<any>(null);
  readonly isHistoryDrawerOpen = signal<boolean>(false);
  readonly isListeningSpeech = signal<boolean>(false);

  // Model Selection Matrix
  readonly selectedCoderModel = signal<string>('qwen.qwen3-coder-30b-a3b-v1:0');
  readonly selectedReviewerModel = signal<string>('anthropic.claude-sonnet-5');
  readonly maxIterations = signal<number>(3);

  // Available models
  readonly availableModels = [
    { id: 'qwen.qwen3-coder-30b-a3b-v1:0', name: 'Qwen 3 Coder 30B (Code Specialist)' },
    { id: 'anthropic.claude-sonnet-5', name: 'Claude Sonnet 5 (Architectural Review)' },
    { id: 'anthropic.claude-haiku-4-5-20251001-v1:0', name: 'Claude Haiku 4.5 (High Speed)' },
    { id: 'meta.llama3-70b-instruct-v1:0', name: 'Llama 3 70B Instruct (General)' },
    { id: 'mistral.devstral-2-123b', name: 'Mistral Devstral 123B (Code Specialist)' },
  ];

  // Effective Language Name
  readonly effectiveLanguage = computed<string>(() => {
    const lang = this.targetLanguage();
    if (lang === 'custom') {
      return this.customLanguageName().trim() || 'Custom Language';
    }
    const found = this.availableLanguages.find((l) => l.id === lang);
    return found ? found.name : lang;
  });

  // Computed Quality Scorecard
  readonly qualityScorecard = computed<QualityScorecard>(() => {
    const feedback = this.reviewFeedback().toUpperCase();
    const exec = this.executionResult();
    const files = this.generatedFiles();
    const sec = this.securityReport();

    if (Object.keys(files).length === 0) {
      return { overallScore: 0, testPassRate: 0, codeQualityScore: 0, securityScore: 0, verdict: 'PENDING' };
    }

    const testPassed = exec ? exec.success : false;
    const testScore = testPassed ? 100 : (exec ? 30 : 50);

    let qualityScore = 85;
    if (feedback.includes('STATUS: PASS')) qualityScore = 96;
    else if (feedback.includes('NEEDS_REVISION')) qualityScore = 65;

    const securityScore = sec ? sec.overall_score : 95;
    const overall = Math.round((testScore * 0.35) + (qualityScore * 0.35) + (securityScore * 0.30));
    const verdict = feedback.includes('STATUS: PASS') ? 'PASS' : (feedback.includes('NEEDS_REVISION') ? 'NEEDS_REVISION' : 'PENDING');

    return {
      overallScore: overall,
      testPassRate: testScore,
      codeQualityScore: qualityScore,
      securityScore: securityScore,
      verdict,
    };
  });

  // Computed active code content
  readonly activeFileContent = computed<string>(() => {
    const iter = this.selectedIteration();
    let fileMap = this.generatedFiles();

    if (iter > 0 && this.iterationHistory().length >= iter) {
      fileMap = this.iterationHistory()[iter - 1]?.files || fileMap;
    }

    const active = this.activeFileName();
    return fileMap[active] || (Object.keys(fileMap).length > 0 ? fileMap[Object.keys(fileMap)[0]] : '');
  });

  // Computed diff lines between current and previous iteration
  readonly diffLines = computed<Array<{ type: 'add' | 'del' | 'same'; text: string; numA?: number; numB?: number }>>(() => {
    if (!this.diffMode()) return [];
    const iter = this.selectedIteration();
    const history = this.iterationHistory();
    const active = this.activeFileName();

    let currentCode = this.activeFileContent();
    let prevCode = '';

    if (iter > 1 && history.length >= iter - 1) {
      prevCode = history[iter - 2]?.files?.[active] || '';
    } else if (iter === 0 && history.length >= 2) {
      prevCode = history[history.length - 2]?.files?.[active] || '';
    }

    if (!prevCode) {
      return currentCode.split('\n').map((line, idx) => ({ type: 'same', text: line, numA: idx + 1, numB: idx + 1 }));
    }

    const linesA = prevCode.split('\n');
    const linesB = currentCode.split('\n');
    const diff: Array<{ type: 'add' | 'del' | 'same'; text: string; numA?: number; numB?: number }> = [];

    let i = 0, j = 0;
    while (i < linesA.length || j < linesB.length) {
      if (i < linesA.length && j < linesB.length && linesA[i] === linesB[j]) {
        diff.push({ type: 'same', text: linesA[i], numA: i + 1, numB: j + 1 });
        i++; j++;
      } else if (j < linesB.length && (!linesA.includes(linesB[j]) || i >= linesA.length)) {
        diff.push({ type: 'add', text: linesB[j], numB: j + 1 });
        j++;
      } else if (i < linesA.length) {
        diff.push({ type: 'del', text: linesA[i], numA: i + 1 });
        i++;
      } else {
        j++;
      }
    }
    return diff;
  });

  constructor() {
    this.checkHealth();
    this.fetchAnalytics();
    this.fetchHistory();
  }

  setTargetLanguage(lang: string): void {
    this.targetLanguage.set(lang);
    if (lang !== 'custom') {
      this.sandboxLanguage.set(lang);
    }
  }

  async checkHealth(): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      if (res.ok) {
        const data = await res.json();
        this.backendHealth.set(data);
      }
    } catch {
      this.backendHealth.set({ status: 'offline', error: 'Unable to reach backend' });
    }
  }

  async fetchHistory(): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/api/workflow/history?limit=30`);
      if (res.ok) {
        const data = await res.json();
        this.historyList.set(data);
      }
    } catch (e) {
      console.warn('Failed to load history list:', e);
    }
  }

  async fetchAnalytics(): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/api/workflow/analytics`);
      if (res.ok) {
        const data = await res.json();
        this.analyticsMetrics.set(data);
      }
    } catch (e) {
      console.warn('Failed to load analytics metrics:', e);
    }
  }

  async loadHistoricalSession(sessionId: string): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/api/workflow/history/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.generated_code && Object.keys(data.generated_code).length > 0) {
          this.generatedFiles.set(data.generated_code);
          this.activeFileName.set(Object.keys(data.generated_code)[0]);
        }
        if (data.review_feedback) {
          this.reviewFeedback.set(data.review_feedback);
        }
        if (data.iterations) {
          this.iterations.set(data.iterations);
        }
        this.currentNode.set('complete');
        this.messages.set([
          {
            id: crypto.randomUUID(),
            sender: 'user',
            content: data.prompt,
            timestamp: new Date(data.created_at || Date.now()),
          },
          {
            id: crypto.randomUUID(),
            sender: 'coder',
            content: `Restored historical session '${sessionId}' from MS SQL Server with ${data.files_count} files.`,
            timestamp: new Date(),
          },
        ]);
        this.isHistoryDrawerOpen.set(false);
        this.runSecurityAudit();
      }
    } catch (e) {
      console.error('Failed to load session detail:', e);
    }
  }

  toggleHistoryDrawer(): void {
    this.isHistoryDrawerOpen.update((v) => !v);
    if (this.isHistoryDrawerOpen()) {
      this.fetchHistory();
      this.fetchAnalytics();
    }
  }

  toggleDiffMode(): void {
    this.diffMode.update((v) => !v);
  }

  setIterationView(iterIndex: number): void {
    this.selectedIteration.set(iterIndex);
  }

  async runSecurityAudit(): Promise<void> {
    const files = this.generatedFiles();
    if (Object.keys(files).length === 0) return;

    this.isRunningSecurity.set(true);
    try {
      const res = await fetch(`${this.baseUrl}/api/workflow/security-scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files }),
      });
      if (res.ok) {
        const data = await res.json();
        this.securityReport.set(data);
      }
    } catch (e) {
      console.error('Failed to run security audit:', e);
    } finally {
      this.isRunningSecurity.set(false);
    }
  }

  async runActiveFileInSandbox(): Promise<void> {
    const code = this.activeFileContent();
    let language = this.sandboxLanguage();
    if (this.targetLanguage() === 'custom') {
      language = this.customLanguageName().trim() || 'python';
    }
    if (!code) return;

    try {
      const res = await fetch(`${this.baseUrl}/api/workflow/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language }),
      });
      if (res.ok) {
        const data = await res.json();
        this.executionResult.set({ ...data, language });
      }
    } catch (e: any) {
      this.executionResult.set({
        success: false,
        exit_code: -1,
        stdout: '',
        stderr: `Failed to execute sandbox: ${e.message}`,
        language,
      });
    }
  }

  async startWorkflow(prompt: string): Promise<void> {
    if (!prompt.trim() || this.isStreaming()) return;

    let languageToSend = this.targetLanguage();
    if (languageToSend === 'custom') {
      languageToSend = this.customLanguageName().trim() || 'python';
    }

    this.isStreaming.set(true);
    this.currentNode.set('init');
    this.currentTokens.set('');
    this.executionResult.set(null);
    this.reviewFeedback.set('');
    this.iterations.set(0);
    this.iterationHistory.set([]);
    this.selectedIteration.set(0);
    this.diffMode.set(false);
    this.securityReport.set(null);

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      sender: 'user',
      content: prompt,
      timestamp: new Date(),
    };
    this.messages.update((msgs) => [...msgs, userMsg]);

    try {
      const response = await fetch(`${this.baseUrl}/api/workflow/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          max_iterations: this.maxIterations(),
          language: languageToSend,
          session_id: `session-${Date.now()}`,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Failed to initiate stream: HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data:')) {
            const rawJson = trimmed.slice(5).trim();
            if (rawJson) {
              try {
                const eventPayload = JSON.parse(rawJson);
                this.handleStreamEvent(eventPayload);
              } catch (parseErr) {
                console.error('SSE parse error:', parseErr);
              }
            }
          }
        }
      }
    } catch (err: any) {
      console.error('Workflow stream execution error:', err);
      this.currentNode.set('error');
      this.messages.update((msgs) => [
        ...msgs,
        {
          id: crypto.randomUUID(),
          sender: 'system',
          content: `Workflow error: ${err.message || 'Stream interrupted.'}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      this.isStreaming.set(false);
      this.checkHealth();
      this.fetchAnalytics();
      this.fetchHistory();
      this.runSecurityAudit();
    }
  }

  private handleStreamEvent(event: any): void {
    const type = event.event;

    if (type === 'start') {
      this.currentNode.set('coder');
    } else if (type === 'node_start') {
      this.currentNode.set(event.node || 'coder');
      this.currentTokens.set('');
    } else if (type === 'token') {
      this.currentTokens.update((t) => t + (event.chunk || ''));
    } else if (type === 'code_update') {
      if (event.generated_code) {
        this.generatedFiles.set(event.generated_code);
        const fileNames = Object.keys(event.generated_code);
        if (fileNames.length > 0 && !event.generated_code[this.activeFileName()]) {
          this.activeFileName.set(fileNames[0]);
        }
      }
      if (event.iterations) {
        this.iterations.set(event.iterations);
      }
      if (event.execution_result) {
        this.executionResult.set(event.execution_result);
      }
      if (event.iteration_history) {
        this.iterationHistory.set(event.iteration_history);
      }
    } else if (type === 'review_update') {
      if (event.review_feedback) {
        this.reviewFeedback.set(event.review_feedback);
      }
      if (event.iterations) {
        this.iterations.set(event.iterations);
      }
    } else if (type === 'complete') {
      this.currentNode.set('complete');
      if (event.generated_code) {
        this.generatedFiles.set(event.generated_code);
      }
      if (event.review_feedback) {
        this.reviewFeedback.set(event.review_feedback);
      }
      if (event.execution_result) {
        this.executionResult.set(event.execution_result);
      }
      if (event.iteration_history) {
        this.iterationHistory.set(event.iteration_history);
      }
      if (event.security_report) {
        this.securityReport.set(event.security_report);
      }
      this.messages.update((msgs) => [
        ...msgs,
        {
          id: crypto.randomUUID(),
          sender: 'coder',
          content: `NexusFlow synthesized ${Object.keys(event.generated_code || {}).length} file(s) across ${event.iterations || 1} iteration(s).`,
          timestamp: new Date(),
        },
      ]);
    } else if (type === 'error') {
      this.currentNode.set('error');
    }
  }

  selectFile(fileName: string): void {
    this.activeFileName.set(fileName);
  }

  downloadProjectBundle(): void {
    const files = this.generatedFiles();
    if (Object.keys(files).length === 0) return;

    for (const [name, content] of Object.entries(files)) {
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    }
  }
}
