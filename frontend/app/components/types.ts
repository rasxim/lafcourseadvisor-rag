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
};

export type StudentProfile = {
  name: string;
  major: string;
  class_year: number;
  overall_gpa: number;
  completed_courses: Course[];
  in_progress_courses: Course[];
  credits: {
    required: number;
    applied: number;
  };
};
