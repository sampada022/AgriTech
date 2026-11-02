import { createContext, useContext } from 'react'
/** true once the preloader has started to open (or when there is no preloader). Hero intro animations wait for it. */
export const IntroContext = createContext(true)
export const useIntro = () => useContext(IntroContext)
