import { useContext } from 'react'
import { UserContext } from '../context/user'

export function useUser() {
  const value = useContext(UserContext)
  if (!value) throw new Error('useUser must be used inside UserProvider')
  return value
}
