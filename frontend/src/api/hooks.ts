import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  analyzeRepository,
  fetchMyRepositories,
  fetchRating,
  fetchRepository,
  reanalyzeRepository,
  type RatingQuery,
} from "./client";

export function useRating(query: RatingQuery) {
  return useQuery({
    queryKey: ["rating", query],
    queryFn: () => fetchRating(query),
  });
}

export function useRepository(id: string | undefined) {
  return useQuery({
    queryKey: ["repository", id],
    queryFn: () => fetchRepository(id as string),
    enabled: Boolean(id),
  });
}

export function useReanalyze(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => reanalyzeRepository(id),
    onSuccess: () => {
      // Упрощённо (без пошагового прогресса, как договорились): просто инвалидируем и
      // перечитываем репозиторий заново после того, как мок-джоба "завершится".
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["repository", id] });
      }, 1200);
    },
  });
}

export function useAnalyzeByUrl() {
  return useMutation({
    mutationFn: (repositoryUrl: string) => analyzeRepository(repositoryUrl),
  });
}

export function useMyRepositories(enabled: boolean) {
  return useQuery({
    queryKey: ["my-repositories"],
    queryFn: fetchMyRepositories,
    enabled,
    retry: false,
  });
}
