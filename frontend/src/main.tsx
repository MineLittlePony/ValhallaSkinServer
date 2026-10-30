import * as preact from 'preact'
import App from './App.tsx'

import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'

preact.render(<App />, document.getElementById('root')!)
