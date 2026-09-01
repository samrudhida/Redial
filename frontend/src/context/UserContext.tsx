import { useEffect, useState, type ReactNode } from 'react'
import { UserContext } from './user'

const STORAGE_KEY = 'redial-user-name'

export function UserProvider({ children }: { children: ReactNode }) {
  const [name, setName] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY))
  useEffect(() => {
    if (name) localStorage.setItem(STORAGE_KEY, name)
  }, [name])
  return <UserContext.Provider value={{ name, setName }}>{children}</UserContext.Provider>
}
