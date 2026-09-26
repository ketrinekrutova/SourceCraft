import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  analyzeRepository,
  deleteToken,
  fetchHistory,
  fetchJob,
  fetchLanguages,
  fetchMyRepositories,
  fetchRating,
  fetchRepository,
  reanalyzeRepository,
  saveOrgs,
  saveToken,
  type RatingQuery,
} from "./client";
import { isActive, type Scope } from "./types";

// Интервал опроса статуса задачи - как рекомендует openapi.yaml (GET /jobs/{id}).
const POLL_MS = 2000;

export function useRating(query: RatingQuery) {
  return useQuery({
    queryKey: ["rating", query],
    queryFn: () => fetchRating(query),
    placeholderData: keepPreviousData,
    refetchInterval: 30_000,
  });
}

export function useLanguages() {
  return useQuery({ queryKey: ["languages"], queryFn: fetchLanguages, staleTime: 60_000 });
}

export function useRepository(id: string | undefined, scope: Scope) {
  return useQuery({
    queryKey: ["repository", id, scope],
    queryFn: () => fetchRepository(id as string, scope),
    enabled: Boolean(id),
    retry: false,
    // Пока анализ в очереди или выполняется - опрашиваем, страница обновится сама по завершении.
    refetchInterval: (query) => (isActive(query.state.data?.latest_job?.status) ? POLL_MS : false),
  });
}

export function useHistory(id: string | undefined, scope: Scope, enabled: boolean) {
  return useQuery({
    queryKey: ["history", id, scope],
    queryFn: () => fetchHistory(id as string, scope),
    enabled: Boolean(id) && enabled,
  });
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => fetchJob(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (query) => (!query.state.data || isActive(query.state.data.status) ? POLL_MS : false),
  });
}

export function useReanalyze(id: string, scope: Scope) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => reanalyzeRepository(id, scope),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repository", id, scope] });
      queryClient.invalidateQueries({ queryKey: ["history", id, scope] });
    },
  });
}

export function useAnalyzeByUrl(scope: Scope) {
  return useMutation({ mutationFn: (repositoryUrl: string) => analyzeRepository(repositoryUrl, scope) });
}

export function useMyRepositories(enabled: boolean) {
  return useQuery({ queryKey: ["my-repositories"], queryFn: fetchMyRepositories, enabled, retry: false });
}

export function useSaveToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveToken,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth"] });
      queryClient.invalidateQueries({ queryKey: ["my-repositories"] });
    },
  });
}

export function useDeleteToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteToken,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth"] });
      queryClient.removeQueries({ queryKey: ["my-repositories"] });
    },
  });
}

export function useSaveOrgs() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveOrgs,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth"] });
      queryClient.invalidateQueries({ queryKey: ["my-repositories"] });
    },
  });
}
