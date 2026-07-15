import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function SyncHistory(){
 const [runs,setRuns]=useState([])
 const load=()=>api.get('/sync/runs').then(r=>setRuns(r.data))
 useEffect(()=>{load(); const id=setInterval(load,5000); return()=>clearInterval(id)},[])
 const run=async()=>{await api.post('/sync/run'); setTimeout(load,800)}
 const fmt = v => v ? new Date(v).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false }) : '-'
 return <><header className="page-header"><div><h1>Lịch sử đồng bộ</h1><p>Tự động chạy mỗi ngày lúc 08:30 (GMT+7)</p></div><button onClick={run}>Đồng bộ ngay</button></header><div className="table-card"><table><thead><tr><th>Thời gian</th><th>Status</th><th>Nguồn</th><th>Insert</th><th>Update</th><th>Skip</th><th>Lỗi</th><th>Clear Sheet</th></tr></thead><tbody>{runs.map(r=><tr key={r.id}><td>{fmt(r.started_at)}</td><td title={r.error_message||''}>{r.status}</td><td>{r.source_rows}</td><td>{r.insert_count}</td><td>{r.update_count}</td><td>{r.skip_count}</td><td>{r.error_count}</td><td>{r.sheet_cleared?'Đã clear':'Chưa clear'}</td></tr>)}</tbody></table></div></>
}
