(() => {
  const TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  async function chooseOldFile() {
    if (window.showOpenFilePicker) {
      const [handle] = await window.showOpenFilePicker({multiple:false,types:[{description:"Excel workbook",accept:{[TYPE]:[".xlsx"]}}]});
      return {file: await handle.getFile(), handle};
    }
    return await new Promise(resolve => { const input=document.createElement('input'); input.type='file'; input.accept='.xlsx'; input.onchange=()=>resolve(input.files?.[0]?{file:input.files[0],handle:null}:null); input.oncancel=()=>resolve(null); input.click(); });
  }
  async function run(button, update) {
    const id=button.dataset.accountExcelSave||button.dataset.accountExcelUpdate;
    const name=button.dataset.accountName||'البند'; const original=button.innerHTML;
    button.disabled=true; button.innerHTML='<span class="spinner-border spinner-border-sm ms-2"></span> جارٍ تجهيز الملف...';
    try {
      let chosen=null;
      if(update){chosen=await chooseOldFile();if(!chosen)return;}
      const form=new FormData();if(chosen?.file)form.append('workbook',chosen.file,chosen.file.name);
      const response=await fetch(`/api/excel-backup/account/${id}/sync`,{method:'POST',headers:{'X-CSRFToken':document.querySelector('meta[name="csrf-token"]')?.content||''},body:form});
      if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.error||'فشل تجهيز ملف Excel.');}
      const blob=await response.blob();
      if(update&&chosen?.handle){
        const handle=chosen.handle; const opts={mode:'readwrite'};
        let permission=await handle.queryPermission(opts); if(permission!=='granted')permission=await handle.requestPermission(opts);
        if(permission!=='granted')throw new Error('لم يتم منح صلاحية تحديث الملف.');
        const writable=await handle.createWritable();await writable.write(blob);await writable.close();
      } else {
        const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`Hesba_Band_${id}_Backup.xlsx`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
      }
      alert(update?(chosen?.handle?'تم تحديث ملف Excel نفسه بنجاح.':'تم تنزيل النسخة المحدثة؛ استبدل بها الملف القديم يدويًا.'):'تم إنشاء ملف Excel الخاص بالبند.');
    } catch(error){if(error.name!=='AbortError')alert(error.message||'حدث خطأ أثناء حفظ Excel.');}
    finally{button.disabled=false;button.innerHTML=original;}
  }
  document.querySelectorAll('[data-account-excel-save]').forEach(b=>b.addEventListener('click',()=>run(b,false)));
  document.querySelectorAll('[data-account-excel-update]').forEach(b=>b.addEventListener('click',()=>run(b,true)));
})();
