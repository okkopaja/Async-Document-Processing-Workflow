import { UploadForm } from '@/components/forms/UploadForm';

export default function UploadPage() {
  return (
    <main className='page'>
      <h1>Upload Documents</h1>
      <p>Use this form to queue documents for asynchronous processing.</p>
      <UploadForm />
    </main>
  );
}
