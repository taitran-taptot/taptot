import { apiFetch } from "./http";
import type { Paginated } from "./types";

export type MyExercise = {
  id: number;
  name_vi: string;
  muscle_group_id: number;
  muscle_name_vi?: string | null;
  exercise_type: string;
  notes_vi?: string | null;
  video_url?: string | null;
  image_url?: string | null;
  gif_url?: string | null;
  instruction_vi?: string | null;
  is_active?: boolean;
  owner_user_id?: string | null;
  is_private?: boolean;
};

export type MyExercisePayload = {
  name_vi: string;
  muscle_group_id: number;
  exercise_type?: string;
  notes_vi?: string | null;
  video_url?: string | null;
  image_url?: string | null;
  gif_url?: string | null;
  instruction_vi?: string | null;
};

export const myExercisesApi = {
  list: (page = 1, pageSize = 12) =>
    apiFetch<Paginated<MyExercise>>(
      `/my-exercises?page=${page}&page_size=${pageSize}`,
      {},
      { auth: true },
    ),
  create: (body: MyExercisePayload) =>
    apiFetch<MyExercise>("/my-exercises", { method: "POST", body: JSON.stringify(body) }, { auth: true }),
  update: (id: number, body: Partial<MyExercisePayload>) =>
    apiFetch<MyExercise>(
      `/my-exercises/${id}`,
      { method: "PATCH", body: JSON.stringify(body) },
      { auth: true },
    ),
  remove: (id: number) =>
    apiFetch<void>(`/my-exercises/${id}`, { method: "DELETE" }, { auth: true }),
};
