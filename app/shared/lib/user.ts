export function getUserId(): string {
  if (typeof window === "undefined") {
    return "server-user" // fallback for SSR
  }

  const key = "docmind_user_id"
  let userId = localStorage.getItem(key)

  if (!userId) {
    userId = crypto.randomUUID()
    localStorage.setItem(key, userId)
  }

  return userId
}