export type Lang = "en" | "ko";
export const LANGS: { code: Lang; label: string }[] = [{ code: "en", label: "English" }, { code: "ko", label: "한국어" }];

const en = {
  appName: "Recursive AI Workspace", language: "Language", signIn: "Sign in", register: "Create account", email: "Email", password: "Password (8+ chars)", signOut: "Sign out",
  project: "Project", newProject: "New project", create: "Create", save: "Save", cancel: "Cancel", delete: "Delete", edit: "Edit", add: "Add", run: "Run", search: "Search", loading: "Loading…", none: "Nothing here yet.", error: "Error",
  navHome: "Home", navCompose: "Compose", navConstraints: "Constraints", navLibrary: "Library", navRefs: "References", navHistory: "History", navSettings: "Settings",
  home: "Home", recentTasks: "Recent tasks", running: "Running now", savedPackages: "Task packages", recentPrompts: "Recent prompts", quickActions: "Quick actions",
  composeTitle: "Prompt composer", intent: "Describe the task in plain language", buildPrompt: "Draft structured prompt", questions: "Questions to clarify", suggestedRefs: "Reference ideas (nothing is fetched or invented)",
  sec_objective: "Objective", sec_context: "Context", sec_instructions: "Instructions", sec_constraints: "Constraints", sec_output_format: "Output format", sec_references: "References", sec_evaluation_criteria: "Evaluation criteria",
  title: "Title", structured: "Structured", compiled: "Compiled", savePrompt: "Save prompt", promptSaved: "Prompt saved", model: "Model", depth: "Validation depth", depth_quick: "Quick", depth_standard: "Standard", depth_deep: "Deep",
  maxIter: "Max rounds", maxCost: "Max cost (USD)", maxSeconds: "Max seconds", reviewer: "Independent reviewer model (optional)", attachRefs: "Attach references", activeConstraints: "Active constraints apply automatically",
  estimate: "Estimate", estCost: "Estimated cost", estTime: "Estimated time", unavailable: "unavailable", costBasis: "Basis", mockNotice: "Mock model: offline simulation, not a real AI. Findings are heuristics.", externalNotice: "Selecting a non-mock model sends your prompt and references to that provider. Enable it in Settings first.",
  execute: "Execute", validation: "Recursive validation", stage: "Current stage", elapsed: "Elapsed", recorded: "Recorded cost", budgetLeft: "Budget left", calls: "API calls", retries: "Retries", rounds: "Rounds", costIncomplete: "(incomplete: some calls had no price)", usageEstimated: "token counts are estimated, not provider-reported",
  state_QUEUED: "Queued", state_RUNNING: "Running", state_WAITING_FOR_APPROVAL: "Waiting for approval", state_COMPLETED: "Completed", state_FAILED: "Failed", state_CANCELLED: "Cancelled",
  v_verified: "Verified", v_partially_verified: "Partially verified", v_unverified: "Unverified", v_failed: "Failed", v_requires_human_review: "Requires human review",
  v_help: "Status reflects deterministic checks plus review findings. LLM review is evidence, not proof.",
  stop_all_checks_passed: "All checks passed", stop_no_improvement: "No improvement", stop_max_iterations: "Max rounds reached", stop_budget: "Budget limit", stop_time_limit: "Time limit", stop_cancelled: "Cancelled", stop_provider_error: "Provider error", stop_budget_unenforceable: "Budget could not be enforced",
  approve: "Approve & start", needsApproval: "Needs your approval before it can start", cancelJob: "Cancel", noFakeProgress: "Progress shows completed stages, not a percentage.",
  issues: "Issues found", repairs: "Repairs applied", compliance: "Constraint compliance", output: "Output", round: "Round", blocking: "blocking", optional: "optional", pass: "pass", fail: "fail", unchecked: "needs review",
  whileWorks: "While AI works", notes: "Scratch notes (saved on this device)", notesPlaceholder: "Plan the next task, jot considerations…", queue: "Task queue", collapse: "Hide panel", expand: "Show panel",
  midChange: "New requirement for a running task", mc_apply_next: "Apply to next run", mc_cancel_restart: "Cancel and restart with it", mc_branch: "Run as a separate branch", midNote: "The running task's rules are frozen and never modified.",
  constraintsTitle: "Constraint registry", content: "Requirement", scope: "Scope", priority: "Priority", severity: "Severity", status: "Status", checkType: "How to verify", version: "Version", versions: "Version history",
  scope_global: "Global", scope_project: "Project", scope_task_package: "Task package", scope_execution: "This execution",
  sev_critical: "Critical", sev_major: "Major", sev_minor: "Minor", st_active: "Active", st_superseded: "Superseded", st_disabled: "Disabled", st_conflicting: "Conflicting", st_pending_approval: "Pending approval",
  ct_semantic: "Semantic (needs review)", ct_required_section: "Required section", ct_must_include: "Must include text", ct_forbidden: "Forbidden text", ct_exact_string: "Exact string", ct_max_chars: "Max characters", ct_min_chars: "Min characters", ct_json_keys: "JSON keys",
  checkParam: "Text / value", conflictFound: "Conflicts with an existing requirement. It is not active yet.", resolveReplace: "Replace existing (kept as superseded)", resolveKeep: "Keep existing, drop this", resolveBoth: "Keep both (priority decides)", overridden: "Temporarily overridden",
  libraryTitle: "Library", favorites: "Favorites", tags: "Tags", folder: "Folder", history_versions: "Versions", compare: "Compare", duplicate: "Duplicate", export: "Export", import: "Import", reuse: "Open in composer", savePackage: "Save as task package", packageName: "Package name", runPackage: "Run package", packageNote: "Packages keep inputs and settings; model outputs are not guaranteed identical.",
  refsTitle: "References", dropHere: "Drop files here or choose", addUrl: "Add URL", role: "Role", r_mandatory_requirement: "Mandatory requirement", r_factual_source: "Factual source", r_example_output: "Example output", r_visual_inspiration: "Visual inspiration", r_background: "Background context", r_negative_example: "Negative example",
  untrustedNote: "Reference content is untrusted data and is never treated as instructions.", missingEvidence: "No factual source attached; claims cannot be traced.", extraction_unsupported: "Stored, but text could not be read",
  historyTitle: "History & reports", reportRequest: "Ask for a report (e.g. “Which requirements changed?”)", generate: "Generate report", reportType: "Report type", rt_full: "Full history", rt_decisions: "Decisions", rt_requirements: "Requirements", rt_validation: "Validation", rt_executive: "Executive summary", download: "Download Markdown", timeline: "Timeline",
  settingsTitle: "Settings", allowExternal: "Allow sending prompts and references to external AI providers", defaultModel: "Default model", retention: "Data retention (days)", deleteAll: "Delete my account and all data", deleteConfirm: "This permanently deletes everything. Continue?", privacy: "Your content is not used for training. API keys live only on the server.",
  license: "License", licenseText: "Licensed under PolyForm Noncommercial 1.0.0. Free for personal, research and educational use; commercial use needs a separate license.",
  apiOffline: "Cannot reach the API. Start it with: npm run api",
} as const;

export type Key = keyof typeof en;
const ko: Record<Key, string> = {
  appName: "재귀 AI 워크스페이스", language: "언어", signIn: "로그인", register: "계정 만들기", email: "이메일", password: "비밀번호 (8자 이상)", signOut: "로그아웃",
  project: "프로젝트", newProject: "새 프로젝트", create: "만들기", save: "저장", cancel: "취소", delete: "삭제", edit: "수정", add: "추가", run: "실행", search: "검색", loading: "불러오는 중…", none: "아직 없습니다.", error: "오류",
  navHome: "홈", navCompose: "작성", navConstraints: "제약", navLibrary: "라이브러리", navRefs: "참고자료", navHistory: "이력", navSettings: "설정",
  home: "홈", recentTasks: "최근 작업", running: "실행 중", savedPackages: "작업 패키지", recentPrompts: "최근 프롬프트", quickActions: "빠른 실행",
  composeTitle: "프롬프트 작성기", intent: "하려는 일을 자연어로 설명하세요", buildPrompt: "구조화된 프롬프트 초안", questions: "확인이 필요한 질문", suggestedRefs: "참고자료 아이디어 (가져오거나 지어내지 않습니다)",
  sec_objective: "목표", sec_context: "맥락", sec_instructions: "지시사항", sec_constraints: "제약", sec_output_format: "출력 형식", sec_references: "참고자료", sec_evaluation_criteria: "평가 기준",
  title: "제목", structured: "구조 편집", compiled: "컴파일 결과", savePrompt: "프롬프트 저장", promptSaved: "프롬프트를 저장했습니다", model: "모델", depth: "검증 깊이", depth_quick: "빠르게", depth_standard: "표준", depth_deep: "깊게",
  maxIter: "최대 라운드", maxCost: "최대 비용 (USD)", maxSeconds: "최대 시간(초)", reviewer: "독립 검토 모델 (선택)", attachRefs: "참고자료 첨부", activeConstraints: "활성 제약은 자동으로 적용됩니다",
  estimate: "예상", estCost: "예상 비용", estTime: "예상 시간", unavailable: "알 수 없음", costBasis: "근거", mockNotice: "모의(mock) 모델: 오프라인 시뮬레이션이며 실제 AI가 아닙니다. 결과는 휴리스틱입니다.", externalNotice: "mock이 아닌 모델을 고르면 프롬프트와 참고자료가 해당 제공자에게 전송됩니다. 먼저 설정에서 허용하세요.",
  execute: "실행", validation: "재귀 검증", stage: "현재 단계", elapsed: "경과 시간", recorded: "기록된 비용", budgetLeft: "남은 예산", calls: "API 호출", retries: "재시도", rounds: "라운드", costIncomplete: "(불완전: 가격 정보가 없는 호출 포함)", usageEstimated: "토큰 수는 제공자 보고값이 아닌 추정치입니다",
  state_QUEUED: "대기 중", state_RUNNING: "실행 중", state_WAITING_FOR_APPROVAL: "승인 대기", state_COMPLETED: "완료", state_FAILED: "실패", state_CANCELLED: "취소됨",
  v_verified: "검증됨", v_partially_verified: "부분 검증", v_unverified: "미검증", v_failed: "실패", v_requires_human_review: "사람 검토 필요",
  v_help: "상태는 결정적 검사와 검토 결과를 반영합니다. LLM 검토는 증거일 뿐 증명이 아닙니다.",
  stop_all_checks_passed: "모든 검사 통과", stop_no_improvement: "개선 없음", stop_max_iterations: "최대 라운드 도달", stop_budget: "예산 한도", stop_time_limit: "시간 한도", stop_cancelled: "취소됨", stop_provider_error: "제공자 오류", stop_budget_unenforceable: "예산을 강제할 수 없음",
  approve: "승인하고 시작", needsApproval: "시작하려면 승인이 필요합니다", cancelJob: "취소", noFakeProgress: "진행률(%)이 아니라 완료된 단계를 표시합니다.",
  issues: "발견된 문제", repairs: "적용된 수정", compliance: "제약 준수", output: "결과", round: "라운드", blocking: "차단", optional: "선택", pass: "통과", fail: "실패", unchecked: "검토 필요",
  whileWorks: "AI가 작업하는 동안", notes: "메모 (이 기기에 저장)", notesPlaceholder: "다음 작업을 계획하거나 고려사항을 적어 두세요…", queue: "작업 큐", collapse: "패널 숨기기", expand: "패널 보기",
  midChange: "실행 중인 작업에 새 요구사항", mc_apply_next: "다음 실행부터 적용", mc_cancel_restart: "취소하고 새 요구사항으로 재시작", mc_branch: "별도 분기로 실행", midNote: "실행 중인 작업의 규칙은 고정되어 절대 바뀌지 않습니다.",
  constraintsTitle: "제약 레지스트리", content: "요구사항", scope: "범위", priority: "우선순위", severity: "심각도", status: "상태", checkType: "검증 방법", version: "버전", versions: "버전 이력",
  scope_global: "전역", scope_project: "프로젝트", scope_task_package: "작업 패키지", scope_execution: "이번 실행",
  sev_critical: "치명", sev_major: "중요", sev_minor: "경미", st_active: "활성", st_superseded: "대체됨", st_disabled: "비활성", st_conflicting: "충돌", st_pending_approval: "승인 대기",
  ct_semantic: "의미 기반 (검토 필요)", ct_required_section: "필수 섹션", ct_must_include: "포함해야 할 텍스트", ct_forbidden: "금지 텍스트", ct_exact_string: "정확한 문자열", ct_max_chars: "최대 글자 수", ct_min_chars: "최소 글자 수", ct_json_keys: "JSON 키",
  checkParam: "텍스트 / 값", conflictFound: "기존 요구사항과 충돌합니다. 아직 활성화되지 않았습니다.", resolveReplace: "기존 항목 교체 (대체됨으로 보존)", resolveKeep: "기존 유지, 이 항목 폐기", resolveBoth: "둘 다 유지 (우선순위로 결정)", overridden: "일시적으로 무시됨",
  libraryTitle: "라이브러리", favorites: "즐겨찾기", tags: "태그", folder: "폴더", history_versions: "버전", compare: "비교", duplicate: "복제", export: "내보내기", import: "가져오기", reuse: "작성기에서 열기", savePackage: "작업 패키지로 저장", packageName: "패키지 이름", runPackage: "패키지 실행", packageNote: "패키지는 입력과 설정을 보존하며, 모델 출력이 동일하다고 보장하지 않습니다.",
  refsTitle: "참고자료", dropHere: "파일을 끌어다 놓거나 선택하세요", addUrl: "URL 추가", role: "역할", r_mandatory_requirement: "필수 요구사항", r_factual_source: "사실 출처", r_example_output: "출력 예시", r_visual_inspiration: "시각적 영감", r_background: "배경 정보", r_negative_example: "나쁜 예시",
  untrustedNote: "참고자료 내용은 신뢰할 수 없는 데이터이며 지시로 취급되지 않습니다.", missingEvidence: "사실 출처가 첨부되지 않아 주장을 추적할 수 없습니다.", extraction_unsupported: "저장됐지만 텍스트를 읽을 수 없음",
  historyTitle: "이력 및 보고서", reportRequest: "보고서 요청 (예: “어떤 요구사항이 바뀌었나?”)", generate: "보고서 생성", reportType: "보고서 유형", rt_full: "전체 이력", rt_decisions: "의사결정", rt_requirements: "요구사항", rt_validation: "검증", rt_executive: "경영 요약", download: "Markdown 다운로드", timeline: "타임라인",
  settingsTitle: "설정", allowExternal: "프롬프트와 참고자료를 외부 AI 제공자에게 보내는 것을 허용", defaultModel: "기본 모델", retention: "데이터 보관 기간(일)", deleteAll: "계정과 모든 데이터 삭제", deleteConfirm: "모든 데이터가 영구 삭제됩니다. 계속할까요?", privacy: "내 콘텐츠는 학습에 쓰이지 않습니다. API 키는 서버에만 있습니다.",
  license: "라이선스", licenseText: "PolyForm Noncommercial 1.0.0 라이선스. 개인·연구·교육 목적은 무료이며, 상업적 이용은 별도 라이선스가 필요합니다.",
  apiOffline: "API에 연결할 수 없습니다. npm run api 로 실행하세요.",
};

export const dict: Record<Lang, Record<Key, string>> = { en, ko };
export function t(lang: Lang, key: Key | string): string {
  return (dict[lang] as Record<string, string>)[key] ?? (dict.en as Record<string, string>)[key] ?? key;
}
export function detectLang(nav?: string): Lang {
  return (nav ?? "").toLowerCase().startsWith("ko") ? "ko" : "en";
}
