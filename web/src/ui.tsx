import { createContext, useContext, useEffect, useState, type ReactNode, type FormEvent } from 'react';
import { AlertCircle, LoaderCircle, MapPin, X } from 'lucide-react';
import { photoUrl, request } from './api';
import type { PlatformConfig, User } from './types';

export const Platform = createContext<{ user: User; config: PlatformConfig; notify: (message: string) => void; navigate: (path: string) => void }>({} as never);
export const usePlatform = () => useContext(Platform);
export const human = (s: string) => s.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
export const date = (s: string | null) => s ? new Date(s).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Not set';
export const isAdmin = (u: User) => ['ADMIN', 'SUPER_ADMIN'].includes(u.role);
export function useData<T>(path: string, initial: T, interval = 15000) {
  const [data, setData] = useState<T>(initial), [error, setError] = useState(''), [loading, setLoading] = useState(true), [version, setVersion] = useState(0);
  useEffect(() => { let active = true; const run = () => request<T>(path).then(d => { if (active) { setData(d); setError(''); } }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); }); run(); const timer = interval ? setInterval(run, interval) : undefined; return () => { active = false; clearInterval(timer); }; }, [path, version, interval]);
  return { data, error, loading, reload: () => setVersion(v => v + 1) };
}
export function ErrorBox({ message }: { message?: string }) { return message ? <div role="alert" className="error"><AlertCircle size={18}/>{message}</div> : null; }
export function Empty({ children }: { children: ReactNode }) { return <div className="empty">{children}</div>; }
export function Badge({ value }: { value: string }) { return <span className={`badge ${value.toLowerCase()}`}>{human(value)}</span>; }
export function PageHead({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) { return <div className="page-head"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>; }
export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  useEffect(() => { const close = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); }; document.addEventListener('keydown', close); return () => document.removeEventListener('keydown', close); }, [onClose]);
  return <div className="modal-backdrop" onClick={onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={e => e.stopPropagation()}><header><h2>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close"><X/></button></header>{children}</section></div>;
}
export function AsyncForm({ onSubmit, children, submit = 'Save', className = '' }: { onSubmit: (data: FormData) => Promise<void>; children: ReactNode; submit?: string; className?: string }) {
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  async function handle(e: FormEvent<HTMLFormElement>) { e.preventDefault(); const data = new FormData(e.currentTarget); setBusy(true); setError(''); try { await onSubmit(data); } catch (err) { setError((err as Error).message); } finally { setBusy(false); } }
  return <form className={`form ${className}`} onSubmit={handle}>{children}<ErrorBox message={error}/><button className="button primary" disabled={busy}>{busy && <LoaderCircle size={16} className="spin"/>}{busy ? 'Saving…' : submit}</button></form>;
}
export const textValue = (f: FormData, key: string) => String(f.get(key) ?? '');
export function LocationFields({ latitude = 8.7139, longitude = 77.7567 }: { latitude?: number; longitude?: number }) {
  const [lat, setLat] = useState(latitude), [lon, setLon] = useState(longitude), [error, setError] = useState('');
  function locate() { if (!navigator.geolocation) { setError('GPS is unavailable. Enter coordinates manually.'); return; } navigator.geolocation.getCurrentPosition(p => { setLat(p.coords.latitude); setLon(p.coords.longitude); setError(''); }, () => setError('Location access was unavailable. You can enter coordinates manually.'), { enableHighAccuracy: false, timeout: 15000 }); }
  return <><div className="field-row"><label>Latitude<input required name="latitude" type="number" step="any" min="-90" max="90" value={lat} onChange={e => setLat(Number(e.target.value))}/></label><label>Longitude<input required name="longitude" type="number" step="any" min="-180" max="180" value={lon} onChange={e => setLon(Number(e.target.value))}/></label></div><button className="button secondary" type="button" onClick={locate}><MapPin size={16}/>Use my current location</button><small>Location is requested only when you press this button. Confirm the issue’s position before submitting.</small><ErrorBox message={error}/></>;
}
export function PrivatePhoto({ id, label }: { id: string | null; label: string }) {
  const [url, setUrl] = useState('');
  useEffect(() => { let active = true, current = ''; setUrl(''); if (id) photoUrl(id).then(u => { current = u; if (active) setUrl(u); else URL.revokeObjectURL(u); }).catch(() => {}); return () => { active = false; if (current) URL.revokeObjectURL(current); }; }, [id]);
  return url ? <img className="evidence" src={url} alt={label}/> : <div className="photo-placeholder">{id ? 'Photograph unavailable' : 'No photograph attached'}</div>;
}
