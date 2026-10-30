import clsx from 'clsx'
import { Fragment } from 'preact'

import { Link } from './elements'

import { useApiRequest } from './utils'
import './App.css'

type SkinType = 'skin' | 'elytra' | 'cape' | (string & {})

type Textures = Record<SkinType, {
  url: string
  metadata: Record<string, string>
}>

function App() {
  const rootClass = clsx(
    'dark:bg-stone-800 light:bg-slate-300 dark:text-neutral-200 light:text-neutral-800',
    'grid grid-rows-[auto_1fr_auto] min-h-screen *:px-4 *:py-2',
  )

  // const [copywriteYear] = useState(() => {
  //   return new Date().getFullYear()
  // })

  const textureData = useApiRequest<Textures>('/api/v1/textures')

  return (
    <>
      <div class={rootClass}>
        <header class="flex items-center gap-4 rounded-lb-xl rounded-rb-xl dark:bg-zinc-900 light:bg-stone-100">
          <Link icon="i-line-md:home" href="https://minelittlepony-mod.com/">Home</Link>
          {{
            pending: () => <div>Loading authentication data</div>,
            error: () => <Link icon="i-line-md:login" href="/api/v1/auth/xbox">Sign in</Link>,
            success: () => <Link icon="i-line-md:logout" href="/api/v1/auth/logout">Sign out</Link>,
          }[textureData.state]()}
        </header>
        <main>
          {textureData.state === 'success'
            ? (
                <>
                  TODO: render the player model using the mson models

                  {['skin', 'elytra'].map(type => (
                    <Fragment key={type}>
                      <h2 class="mb-2 mt-4 text-lg font-semibold capitalize">{type}</h2>
                      {type in textureData.data
                        ? (
                            <>
                              <img src={textureData.data[type].url} />
                              <pre>{JSON.stringify(textureData.data[type].metadata, undefined, 2)}</pre>
                            </>
                          )
                        : <>No data</>}
                    </Fragment>
                  ))}
                </>
              )
            : undefined}
        </main>
        <footer className="flex items-center justify-center gap-2">
          &copy;
          {' '}
          &ndash;
          {' '}
          MineLittlePony Team
        </footer>
      </div>
    </>
  )
}

export default App
