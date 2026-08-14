import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'
import { AuthProvider } from './lib/auth'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

// Ao focar um campo numérico, seleciona o conteúdo — assim digitar substitui o "0"
// (evita ficar "039,99"). O timeout garante que a seleção venha após o clique posicionar o cursor.
document.addEventListener('focusin', (e) => {
  const el = e.target as HTMLElement
  if (el instanceof HTMLInputElement && el.type === 'number') {
    setTimeout(() => {
      try {
        el.select()
      } catch {
        /* alguns navegadores não permitem select em type=number; ignora */
      }
    }, 0)
  }
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
