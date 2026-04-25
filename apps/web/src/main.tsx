import { createRoot } from 'react-dom/client';
import { Toaster } from 'sonner';
import App from './app/App';
import { CopyToastProvider } from './app/components/CopyToastProvider';
import './styles/index.css';

createRoot(document.getElementById('root')!).render(
  <CopyToastProvider>
    <App />
    <Toaster richColors position="top-center" />
  </CopyToastProvider>,
);
