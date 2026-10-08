import { post } from '../../../web/src/api';
import { AsyncForm, ErrorBox, PageHead, isAdmin, textValue, useData, usePlatform } from '../../../web/src/ui';

export default function Flood() {
  const { user, notify } = usePlatform();
  const records = useData<{id:string;station:string;level_m:number;source:string;created_at:string}[]>('/flood-monitoring/readings', []);
  return <><PageHead eyebrow="COMMUNITY MODULE / EXAMPLE" title="Flood monitoring" description="Manual gauge records demonstrate an independent extension. No live sensor or flood forecast is connected."/><ErrorBox message={records.error}/><div className="two-column"><section className="panel form-panel">{isAdmin(user) ? <AsyncForm submit="Record reading" onSubmit={async f=>{await post('/flood-monitoring/readings',{station:textValue(f,'station'),level_m:Number(f.get('level_m')),source:textValue(f,'source')});records.reload();notify('Reading recorded');}}><label>Station<input required name="station" minLength={3}/></label><label>Water level (metres)<input required name="level_m" type="number" step="0.01" min={0} max={100}/></label><label>Source / observation reference<input required name="source" minLength={5}/></label></AsyncForm> : <p>Administrators can enter readings. This module does not issue flood warnings.</p>}</section><section className="panel form-panel"><h2>Recorded readings</h2>{records.data.map(r=><div className="record" key={r.id}><strong>{r.station} · {r.level_m} m</strong><p>{r.source}</p><small>{new Date(r.created_at).toLocaleString()}</small></div>)}</section></div></>;
}
