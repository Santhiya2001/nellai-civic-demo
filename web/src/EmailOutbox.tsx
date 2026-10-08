import { useState } from 'react';
import { Mail, RefreshCw } from 'lucide-react';
import { Badge, Empty, ErrorBox, PageHead, useData, usePlatform } from './ui';

interface Alert {
  id: string; complaint_id: string; reference: string; title: string; recipient: string;
  state: string; attempts: number; created_at: string; sent_at: string | null;
  subject: string; body: string;
}
interface Outbox {
  recipient: string | null; delivery_configured: boolean;
  counts: Record<string, number>; messages: Alert[];
}

export function EmailOutbox() {
  const { navigate } = usePlatform();
  const [selected, setSelected] = useState('');
  const outbox = useData<Outbox | null>('/complaint-emails', null);
  const data = outbox.data;
  const message = data?.messages.find(m => m.id === selected) || data?.messages[0];
  return <>
    <PageHead eyebrow="AUTHORITY NOTIFICATIONS" title="Every report reaches the outbox."
      description="Review complaint alerts, their recipients, and delivery status."
      action={<button className="button secondary" onClick={outbox.reload}><RefreshCw size={16}/>Refresh outbox</button>}/>
    <ErrorBox message={outbox.error}/>
    {data && <>
      <div className={`email-status ${data.delivery_configured ? 'configured' : ''}`} role="status">
        <Mail size={26}/><div>
          <strong>{data.delivery_configured ? 'Email sending is configured' : 'Preview only — email sending is not connected'}</strong>
          <p>{data.delivery_configured
            ? 'The worker checks queued alerts about every 30 seconds. Mail-server acceptance does not confirm inbox delivery.'
            : 'New complaints are saved in this outbox. Pending messages have not been sent to Gmail.'}</p>
          <small>New complaint recipient: {data.recipient || 'Not configured'}</small>
        </div>
      </div>
      <div className="email-metrics">
        {[['PENDING', 'Waiting to send'], ['SENT', 'Accepted by mail server'], ['FAILED', 'Delivery failed']].map(([key, label]) =>
          <section className="metric" key={key}><span>{label}</span><strong>{data.counts[key] || 0}</strong></section>)}
      </div>
      <div className="email-layout">
        <section className="panel email-list"><header className="panel-head"><h2>Latest complaint alerts</h2><small>Latest 100</small></header>
          {data.messages.map(m => <button key={m.id} className={`email-item ${message?.id === m.id ? 'selected' : ''}`}
            onClick={() => setSelected(m.id)} aria-pressed={message?.id === m.id}>
            <span className="email-item-top"><strong>{m.reference}</strong><Badge value={m.state}/></span>
            <span>{m.title}</span><small>{new Date(m.created_at).toLocaleString('en-IN')}</small>
          </button>)}
          {!data.messages.length && <Empty>Submit a complaint to create its authority email alert.</Empty>}
        </section>
        <section className="panel email-preview" aria-label="Email preview">
          {message ? <>
            <header className="panel-head"><div><span className="eyebrow">MESSAGE PREVIEW</span><h2>{message.subject}</h2></div><Badge value={message.state}/></header>
            <dl className="email-envelope"><div><dt>To</dt><dd>{message.recipient}</dd></div>
              <div><dt>Delivery</dt><dd>{message.state === 'SENT' ? 'Accepted by the mail server' : message.state === 'FAILED' ? 'Delivery failed' : 'Not sent — waiting in the outbox'}</dd></div>
              <div><dt>Attempts</dt><dd>{message.attempts}</dd></div></dl>
            <pre className="email-body">{message.body}</pre>
            <footer className="email-preview-footer"><button className="button secondary" onClick={() => navigate(`complaints/${message.complaint_id}`)}>Open complaint</button></footer>
          </> : <Empty>Select an alert to preview its message.</Empty>}
        </section>
      </div>
    </>}
    {!data && !outbox.error && <Empty>Loading email outbox…</Empty>}
  </>;
}
