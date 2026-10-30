import { hydrate, prerender as ssr } from 'preact-iso'
import App from './App.tsx'

import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'

if (typeof window !== 'undefined') {
  hydrate(<App />, document.getElementById('root')!)
}

export async function prerender(data: any) {
  return await ssr(<App {...data} />)
}
