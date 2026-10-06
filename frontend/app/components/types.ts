export type Source = {
  text: string;
  score: number;
  start_page: number;
  end_page: number;
  heading_path: string;
  section: string;
  metadata: Record<string, unknown>;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  createdAt: number;
};

export type Course = {
  code: string;
  title: string;
  grade?: string;
  credits: number;
  term?: string;
  note?: string;
};

export type Requirement = {
  block: string;
  status: string;
  still_needed: string[];
  credits_required?: number;
  credits_applied?: number;
  classes_required?: number;
  classes_applied?: number;
  unmet_conditions?: string;
  notes?: string[];
};

export type StudentProfile = {
  name: string;
  major: string;
  class_year: number;
  overall_gpa: number;
  degree?: string;
  minor?: string;
  expected_graduation?: string;
  advisor?: string;
  catalog_year?: string;
  audit_date?: string;
  major_gpa?: number;
  completed_courses: Course[];
  in_progress_courses: Course[];
  requirements?: Requirement[];
  credits: {
    required: number;
    applied: number;
    still_needed?: number;
  };
};
