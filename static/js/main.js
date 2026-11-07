(() => {
 const reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 // Slide the pink active marker to the selected navigation item.
 const sideNav=document.getElementById('sideNav');
 const rail=document.querySelector('.sidebar');
 const marker=sideNav?.querySelector('.nav-active-indicator');
 const moveMarker=()=>{
   const active=sideNav?.querySelector('.side-link.active');
   if(!active||!marker||!rail)return;
   const navRect=sideNav.getBoundingClientRect(), linkRect=active.getBoundingClientRect();
   marker.style.opacity='1';
   marker.style.transform=`translate3d(0,${linkRect.top-navRect.top+12}px,0)`;
   marker.style.height=`${Math.max(22,linkRect.height-24)}px`;
 };
 if(marker){
   requestAnimationFrame(()=>requestAnimationFrame(moveMarker));
   window.addEventListener('resize',moveMarker,{passive:true});
 }

 const targets='.section,.promo-layout,.advertising-section,.advert-banner,.studio-header,.studio-stats,.studio-list-section,.creation-form,.auth-card,.auth-visual,.product-ad-hero,.product-detail-top,.screenshot-section,.app-details-section,.additional-info-grid';
 if(!reduceMotion&&'IntersectionObserver'in window){const ob=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-visible');ob.unobserve(e.target)}}),{threshold:.08,rootMargin:'0px 0px -35px 0px'});document.querySelectorAll(targets).forEach(e=>{e.classList.add('reveal');ob.observe(e)})}
 document.querySelectorAll('.promo-layout>a,.category-item,.store-product,.catalog-item,.studio-item,.stat-card,.advert-banner').forEach((e,i)=>{if(!reduceMotion)e.style.setProperty('--stagger',`${Math.min(i,12)*45}ms`)});
 const mf=document.getElementById('mainFile'),mn=document.getElementById('mainFileName');
 if(mf&&mn)mf.addEventListener('change',()=>{const f=mf.files&&mf.files[0];mn.textContent=f?`${f.name} · ${(f.size/1048576).toFixed(2)} MB`:'No file selected';mf.closest('.drop-zone')?.classList.toggle('has-file',!!f)});
 const preview=(f,t,append=false)=>{if(!f.type.startsWith('image/'))return;const r=new FileReader();r.onload=e=>{const im=document.createElement('img');im.src=e.target.result;im.alt=f.name;im.title=f.name;if(!append)t.replaceChildren();t.appendChild(im)};r.readAsDataURL(f)};
 document.querySelectorAll('input[type=file][data-preview]').forEach(i=>i.addEventListener('change',()=>{const t=document.getElementById(i.dataset.preview);if(t&&i.files[0])preview(i.files[0],t)}));
 const si=document.getElementById('screenshotsInput'),sp=document.getElementById('screenshotPreview');if(si&&sp)si.addEventListener('change',()=>{sp.replaceChildren();[...si.files].forEach(f=>preview(f,sp,true))});
 document.querySelectorAll('[data-scroll]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.scroll)?.scrollBy({left:Number(b.dataset.dir)*330,behavior:reduceMotion?'auto':'smooth'})));
 document.querySelectorAll('.screenshot-card').forEach(b=>b.addEventListener('click',()=>{const x=document.getElementById('lightbox');if(x){x.querySelector('img').src=b.dataset.src;x.classList.add('open');document.body.classList.add('modal-open')}}));
 const box=document.getElementById('lightbox'),close=()=>{box?.classList.remove('open');document.body.classList.remove('modal-open')};box?.addEventListener('click',e=>{if(e.target===box||e.target.closest('button'))close()});document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
 document.querySelectorAll('form').forEach(f=>f.addEventListener('submit',()=>{if(!f.checkValidity())return;const b=f.querySelector('button[type=submit],button:not([type])');if(b&&!b.dataset.noLoading){b.classList.add('is-loading');b.disabled=true;b.setAttribute('aria-busy','true')}}));
})();