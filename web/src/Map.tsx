import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet.markercluster';
import 'leaflet.heat';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { request } from './api';
import { ErrorBox, human } from './ui';

type Feature = { geometry: { coordinates: [number, number] }; properties: { reference: string; category: string; status: string } };
export default function CivicMap({ compact = false }: { compact?: boolean }) {
  const el = useRef<HTMLDivElement>(null), [error, setError] = useState('');
  useEffect(() => {
    if (!el.current) return;
    const map = L.map(el.current, { scrollWheelZoom: !compact }).setView([8.7139, 77.7567], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 19 }).addTo(map);
    const clusters = L.markerClusterGroup().addTo(map), trees = L.layerGroup(), water = L.layerGroup(), boundaries = L.layerGroup();
    let active = true;
    const safePopup = (title: string, subtitle: string) => { const d = document.createElement('div'); const b = document.createElement('strong'); b.textContent = title; d.append(b, document.createElement('br'), document.createTextNode(subtitle)); return d; };
    Promise.all([request<{features: Feature[]}>('/map'), request<{id: string; enabled: boolean}[]>('/modules')]).then(async ([geo, modules]) => {
      if (!active) return;
      geo.features.forEach(f => { const [lon, lat] = f.geometry.coordinates; const marker = L.marker([lat, lon], { icon: L.divIcon({ className: 'issue-pin', html: '<span></span>', iconSize: [22, 22] }) }); marker.bindPopup(safePopup(f.properties.reference, human(f.properties.category) + ' · ' + human(f.properties.status))); clusters.addLayer(marker); });
      const heat = L.heatLayer(geo.features.map(f => [f.geometry.coordinates[1], f.geometry.coordinates[0], 0.7] as [number, number, number]), { radius: 30, blur: 22 });
      L.control.layers({}, { 'Issue clusters': clusters, 'Issue heatmap': heat, 'Trees': trees, 'Water bodies': water, 'Boundaries': boundaries }, { collapsed: compact }).addTo(map);
      for (const [id, path, layer, title, color] of [['green', '/trees', trees, 'species', '#31865a'], ['water', '/water-bodies', water, 'name', '#277ca2']] as const) {
        if (modules.some(m => m.id === id && m.enabled)) { const rows = await request<Record<string, string | number>[]>(path); if (!active) return; rows.forEach(p => L.circleMarker([Number(p.latitude), Number(p.longitude)], { radius: 7, color, fillOpacity: 0.8 }).bindPopup(safePopup(String(p[title]), id === 'green' ? 'Registered tree' : 'Water resource')).addTo(layer)); layer.addTo(map); }
      }
      const bounds = await request<{ name: string; geojson: GeoJSON.GeoJsonObject; verified: boolean }[]>('/boundaries');
      if (active) bounds.forEach(b => L.geoJSON(b.geojson, { style: { color: '#799a60', weight: 2, fillOpacity: 0.04, dashArray: '6 6' } }).bindPopup(safePopup(b.name, b.verified ? 'Verified boundary' : 'Unverified / illustrative boundary')).addTo(boundaries));
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; map.remove(); };
  }, [compact]);
  return <div className={compact ? 'map-wrap compact' : 'map-wrap'}><ErrorBox message={error}/><div ref={el} className="map"/><div className="map-foot"><span><i className="dot"/> Community issue locations</span><span>Public locations are approximate · Base map needs internet</span></div></div>;
}
