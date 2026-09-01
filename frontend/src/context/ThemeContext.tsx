import { useEffect, useState, type ReactNode } from 'react'
import { ThemeContext, type Theme } from './theme'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('redial-theme')
    return saved === 'dark' || saved === 'light' ? saved : 'dark'
  })
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('redial-theme', theme) }, [theme])
  return <ThemeContext.Provider value={{ theme, toggleTheme: () => setTheme(value => value === 'light' ? 'dark' : 'light') }}>{children}</ThemeContext.Provider>
}
