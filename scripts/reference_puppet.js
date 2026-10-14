/* A single set of drawings, animated by two-bone joints. No frame morphing. */
const canvas = document.querySelector('canvas');
const ctx = canvas.getContext('2d');
const atlas = new Image();
let parts = [], paused = false, phase = 0, action = 'walk', speed = 1, previous = 0;
const add = (a,b) => [a[0]+b[0], a[1]+b[1]];
const length = a => Math.hypot(...a);

function components(image) {
  const c=document.createElement('canvas');c.width=image.width;c.height=image.height;
  const g=c.getContext('2d');g.drawImage(image,0,0);
  const pixels=g.getImageData(0,0,c.width,c.height).data;
  const visited=new Uint8Array(c.width*c.height), queue=new Int32Array(visited.length), found=[];
  for(let start=0;start<visited.length;start++) {
    if(visited[start] || pixels[start*4+3]<128)continue;
    let head=0,tail=1,x0=c.width,y0=c.height,x1=0,y1=0;
    queue[0]=start;visited[start]=1;
    while(head<tail) {
      const index=queue[head++],x=index%c.width,y=Math.floor(index/c.width);
      x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);
      for(const next of [x>0?index-1:-1,x<c.width-1?index+1:-1,y>0?index-c.width:-1,y<c.height-1?index+c.width:-1]) {
        if(next>=0 && !visited[next] && pixels[next*4+3]>=128){visited[next]=1;queue[tail++]=next;}
      }
    }
    if(tail>500)found.push({x:x0,y:y0,w:x1-x0+1,h:y1-y0+1,count:tail});
  }
  const biggest=found.sort((a,b)=>b.count-a.count).slice(0,10);
  const upper=biggest.filter(a=>a.y+a.h/2<c.height/2).sort((a,b)=>a.x-b.x);
  const lower=biggest.filter(a=>a.y+a.h/2>=c.height/2).sort((a,b)=>a.x-b.x);
  if(upper.length!==5 || lower.length!==5)throw new Error('Expected ten isolated puppet parts');
  return [...upper,...lower];
}

function joint(a,b,l1,l2,bend=1) {
  const dx=b[0]-a[0],dy=b[1]-a[1],d=Math.hypot(dx,dy);
  if(d>=l1+l2 || d<=Math.abs(l1-l2))throw new Error('Joint target outside reach');
  const along=(l1*l1-l2*l2+d*d)/(2*d), perpendicular=Math.sqrt(l1*l1-along*along);
  return [a[0]+dx/d*along+bend*dy/d*perpendicular,
          a[1]+dy/d*along-bend*dx/d*perpendicular];
}

function part(index,point,scale,pivot=[.5,.5],angle=0,region=null) {
  const p=parts[index];
  ctx.save();ctx.translate(...point);ctx.rotate(angle);ctx.scale(scale,scale);
  if(region){ctx.beginPath();ctx.rect((region[0]-pivot[0])*p.w,(region[1]-pivot[1])*p.h,region[2]*p.w,region[3]*p.h);ctx.clip();}
  ctx.drawImage(atlas,p.x,p.y,p.w,p.h,-p.w*pivot[0],-p.h*pivot[1],p.w,p.h);
  ctx.restore();
}

function segment(index,a,b,anchor,end,region=null) {
  const p=parts[index], source=[(end[0]-anchor[0])*p.w,(end[1]-anchor[1])*p.h];
  const target=[b[0]-a[0],b[1]-a[1]], scale=length(target)/length(source);
  const angle=Math.atan2(-target[0],target[1])-Math.atan2(-source[0],source[1]);
  part(index,a,scale,anchor,angle,region);
}

function gait(t) {
  const p=((t%1)+1)%1;
  if(action==='idle')return {step:0,lift:0};
  if(p<=.5)return {step:34-136*p,lift:0};
  const u=(p-.5)*2;
  // Match the stance velocity at takeoff and landing; zero lift velocity at
  // both ends prevents the old foot kick at the boundary between phases.
  return {step:-34+68*(6*u*u-4*u*u*u-u),lift:24*Math.sin(Math.PI*u)**2};
}

function pose(t) {
  const bob=action==='idle'?Math.sin(t*Math.PI*2)*.8:2*Math.cos(t*Math.PI*4);
  const limbs={};
  for(const [side,offset] of [['near',0],['far',.5]]) {
    const near=side==='near', foot=gait(t+offset);
    const hip=[near?240:272,288+bob];
    const ankle=[(near?238:274)+foot.step*.95,(near?432:427)+foot.step*.13-foot.lift];
    const knee=joint(hip,ankle,77,77,1);
    const shoulder=[near?213:300,194+bob];
    const swing=action==='idle'?0:-20*Math.cos((t+offset)*Math.PI*2);
    const wrist=[shoulder[0]+(near?-12:12)+swing,296+bob+swing*.13];
    const elbow=joint(shoulder,wrist,55,55,near?-1:1);
    limbs[side]={hip,knee,ankle,shoulder,elbow,wrist,foot};
  }
  return {bob,limbs};
}

function leg(side,p) {
  const near=side==='near';
  const index=near?7:9,asset=parts[index];
  const scale=77/Math.hypot(.03*asset.w,.67*asset.h);
  // A planted shoe stays level instead of rotating with the lower leg.
  part(index,p.ankle,scale,[.43,.76],-.16*p.foot.lift/24,[0,.64,1,.36]);
  segment(index,p.knee,p.ankle,[.40,.09],[.43,.76],[0,0,1,.75]);
  segment(near?6:8,p.hip,p.knee,[.54,.08],[.52,.92]);
}

function arm(side,p) {
  const near=side==='near';
  segment(near?3:5,p.elbow,p.wrist,[.48,.09],[.50,.73]);
  segment(near?2:4,p.shoulder,p.elbow,near?[.63,.09]:[.32,.09],near?[.43,.93]:[.60,.93]);
}

function render(t,opaque=false) {
  if(!parts.length)return;
  ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,512,512);
  if(opaque){ctx.fillStyle='#283340';ctx.fillRect(0,0,512,512);}
  ctx.imageSmoothingEnabled=false;
  const current=pose(t),p=current.limbs,bob=Math.round(current.bob);
  arm('far',p.far);leg('far',p.far);leg('near',p.near);
  // The pelvis covers both hip attachments; the torso never changes drawing.
  part(1,[256,169+bob],133/parts[1].h,[.5,.06],0,[0,0,1,.96]);
  arm('near',p.near);
  // One immutable head bitmap, translated by integer pixels only.
  part(0,[256,178+bob],156/parts[0].h,[.5,.96]);
  document.querySelector('#frame').textContent=`${Math.floor((((t%1)+1)%1)*32)+1} / 32`;
  return current;
}

function loop(time) {
  if(previous && !paused)phase=(phase+(time-previous)/960*speed)%1;
  previous=time;render(phase);requestAnimationFrame(loop);
}

document.querySelector('#pause').onclick=()=>{paused=!paused;document.querySelector('#pause').textContent=paused?'Reproduzir':'Pausar';};
document.querySelector('#step').onclick=()=>{paused=true;phase=(Math.floor(phase*32)+1)%32/32;document.querySelector('#pause').textContent='Reproduzir';render(phase);};
document.querySelector('#action').onchange=e=>{action=e.target.value;phase=0;};
document.querySelector('#speed').oninput=e=>{speed=Number(e.target.value);document.querySelector('#rate').textContent=speed.toFixed(2)+'×';};
window.puppet={render,pose,setAction(value){action=value;},seek(t){paused=true;phase=t;render(t);document.querySelector('#pause').textContent='Reproduzir';},ready:false};
atlas.onload=()=>{parts=components(atlas);window.puppet.parts=parts;window.puppet.ready=true;render(0);requestAnimationFrame(loop);};
atlas.src=window.ATLAS_DATA;
