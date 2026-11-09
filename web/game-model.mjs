export const MINI_GAMES={
 stars:{name:'接住星光',description:'15 秒内点亮星星，陪拉姆开心一下。',duration:15000,symbol:'✦'},
 memory:{name:'记忆翻翻乐',duration:30000,symbol:'▦'},
 rhythm:{name:'节奏拍手',duration:15000,symbol:'♪'},
 penalty:{name:'拉姆点球赛',description:'20 秒内不限射门次数，进 8 球可领奖。',duration:20000,symbol:'⚽'}
};
export function shuffled(values,random=Math.random){const a=[...values];for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.max(0,Math.min(.999999,random()))*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
export function memoryRound(random=Math.random){return {cards:shuffled([180001,180002,180017,180010,180001,180002,180017,180010],random),open:[],matched:[],pairs:0,actions:0,hideAt:0,completedAtMs:null};}
export function refreshMemory(m,now){if(m.hideAt&&now>=m.hideAt){m.open=[];m.hideAt=0;return true;}return false;}
export function flipMemory(m,index,now){refreshMemory(m,now);if(!Number.isInteger(index)||index<0||index>=8||m.hideAt||m.open.includes(index)||m.matched.includes(index))return false;m.actions++;m.open.push(index);if(m.open.length===2){const [a,b]=m.open;if(m.cards[a]===m.cards[b]){m.matched.push(a,b);m.pairs++;if(m.pairs===4&&m.completedAtMs==null)m.completedAtMs=now;m.open=[];}else m.hideAt=now+850;}return true;}
export function rhythmState(m,elapsed){
 const segments=m.rhythmSegments||[{at:0,phase:0,speed:1}];let seg=segments[0];for(const item of segments){if(item.at>elapsed)break;seg=item;}
 const phase=seg.phase+Math.max(0,elapsed-seg.at)/1800*seg.speed;
 return {phase,beat:Math.floor(phase),position:phase%1};
}
export const rhythmPosition=(elapsed,m={})=>rhythmState(m,Math.max(0,elapsed)).position;
export const RHYTHM_HALF_WIDTH=.08;
export const rhythmHalfWidth=m=>Math.max(.035,RHYTHM_HALF_WIDTH-(m.score||0)*.006);
export function rhythmHit(m,elapsed,random=Math.random){
 if(!Number.isFinite(elapsed)||elapsed<0||elapsed>=MINI_GAMES.rhythm.duration)return null;
 const current=rhythmState(m,elapsed);
 m.actions++;
 // A miss leaves the green zone in place. Each pass through it can score once.
 if(current.beat===m.lastScoredBeat||Math.abs(current.position-(m.target??.5))>rhythmHalfWidth(m)+1e-9)return false;
 m.lastScoredBeat=current.beat;
 m.score++;
 m.rhythmSegments??=[{at:0,phase:0,speed:1}];
 m.rhythmSegments.push({at:elapsed,phase:current.phase,speed:1+m.score*.15});
 const delta=(random()<.5?-1:1)*(.05+Math.max(0,Math.min(1,random()))*.035),next=(m.target??.5)+delta;
 m.target=next<.3?.6-next:next>.7?1.4-next:next;return true;
}
export function keeperPhase(elapsed,m){const segments=m?.keeperSegments||[{at:0,phase:0,speed:1}];let segment=segments[0];for(const entry of segments){if(entry.at>elapsed)break;segment=entry;}return segment.phase+(elapsed-segment.at)/650*segment.speed;}
export const keeperPosition=(elapsed,m)=>.5+Math.sin(keeperPhase(elapsed,m))*.32;
export function penaltyShot(m,zone,elapsed){
 if(![0,1,2].includes(zone)||!Number.isFinite(elapsed)||elapsed<0||elapsed>=20000||elapsed<m.readyAt)return null;
 const target=[.18,.5,.82][zone],landing=elapsed+550,saved=Math.abs(target-keeperPosition(landing,m))<.2;
 m.shots++;m.actions++;m.readyAt=elapsed+1200;
 if(!saved){const phase=keeperPhase(landing,m);m.score++;m.keeperSegments??=[{at:0,phase:0,speed:1}];m.keeperSegments.push({at:landing,phase,speed:1+m.score*.18});}
 return {goal:!saved,target};
}
