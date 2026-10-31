(() => {
  const saveButton = document.getElementById("excelSaveBtn");
  const updateButton = document.getElementById("excelUpdateBtn");
  if (!saveButton || !updateButton) return;
  const DB_NAME = "family-expense-backup", STORE = "handles", KEY = "workbook";
  const DB_SUPPORTED = "indexedDB" in window;
  const XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const PICKER_TYPES = [{ description: "Excel workbook", accept: { [XLSX_TYPE]: [".xlsx"] } }];
  let fileHandle = null;

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  async function getHandle() {
    if (!DB_SUPPORTED) return null;
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const req = db.transaction(STORE, "readonly").objectStore(STORE).get(KEY);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
  }
  async function storeHandle(handle) {
    if (!DB_SUPPORTED) return;
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(handle, KEY);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }
  async function clearHandle() {
    fileHandle = null;
    if (!DB_SUPPORTED) return;
    const db = await openDb();
    return new Promise(resolve => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(KEY);
      tx.oncomplete = resolve;
      tx.onerror = resolve;
    });
  }
  async function permission(handle) {
    const options = { mode: "readwrite" };
    if (await handle.queryPermission(options) === "granted") return true;
    return (await handle.requestPermission(options)) === "granted";
  }
  async function writeFile(handle, blob) {
    const writable = await handle.createWritable();
    try { await writable.write(blob); await writable.close(); }
    catch (error) { try { await writable.abort(); } catch (_) {} throw error; }
  }
  function chooseFileFallback() {
    return new Promise(resolve => {
      const picker = document.createElement("input");
      picker.type = "file"; picker.accept = ".xlsx";
      picker.onchange = () => resolve(picker.files?.[0] || null);
      picker.oncancel = () => resolve(null);
      picker.click();
    });
  }
  async function getUpdateFile() {
    if (fileHandle) {
      try {
        if (!(await permission(fileHandle))) throw new Error("لم يتم منح صلاحية تعديل ملف Excel.");
        return await fileHandle.getFile();
      } catch (error) {
        if (error.name === "NotFoundError") {
          await clearHandle();
          throw new Error("ملف النسخة الاحتياطية الأصلي لم يعد موجودًا. اضغط تحديث مرة أخرى واختر ملف Excel الصحيح، أو أنشئ نسخة جديدة.");
        }
        throw error;
      }
    }
    if (window.showOpenFilePicker) {
      const [handle] = await window.showOpenFilePicker({ multiple: false, types: PICKER_TYPES });
      fileHandle = handle;
      await storeHandle(handle);
      if (!(await permission(handle))) throw new Error("لم يتم منح صلاحية تعديل ملف Excel.");
      return await handle.getFile();
    }
    return await chooseFileFallback();
  }
  async function requestWorkbook(existingFile) {
    const form = new FormData();
    if (existingFile) form.append("workbook", existingFile, existingFile.name);
    const response = await fetch("/api/excel-backup/sync", {
      method: "POST",
      headers: { "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || "" },
      body: form
    });
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.error || "فشل تجهيز ملف Excel.");
    }
    return response.blob();
  }
  function downloadBlob(blob) {
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = "Hesba_Backup.xlsx";
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function run(action, button) {
    const originalText = button.innerHTML;
    saveButton.disabled = updateButton.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm ms-2"></span> جارٍ تجهيز النسخة...';
    try {
      if (action === "save" && window.showSaveFilePicker) {
        // Invoke the native picker directly from the click, before awaiting network work.
        const handle = await window.showSaveFilePicker({ suggestedName: "Hesba_Backup.xlsx", types: PICKER_TYPES });
        const blob = await requestWorkbook(null);
        await writeFile(handle, blob);
        fileHandle = handle;
        await storeHandle(handle);
      } else {
        if (action === "update" && !fileHandle && DB_SUPPORTED) fileHandle = await getHandle();
        const existingFile = action === "update" ? await getUpdateFile() : null;
        if (action === "update" && !existingFile) throw new Error("لم يتم اختيار ملف Excel للتحديث.");
        const blob = await requestWorkbook(existingFile);
        if (action === "update" && fileHandle && window.showSaveFilePicker) await writeFile(fileHandle, blob);
        else downloadBlob(blob);
      }
      alert(action === "save" ? "تم إنشاء وحفظ نسخة Excel جديدة بنجاح." : "تم تحديث نسخة Excel بنجاح.");
    } catch (error) {
      if (error.name !== "AbortError") alert(error.message || "حدث خطأ أثناء النسخ الاحتياطي.");
    } finally {
      saveButton.disabled = updateButton.disabled = false;
      button.innerHTML = originalText;
    }
  }
  saveButton.addEventListener("click", () => run("save", saveButton));
  updateButton.addEventListener("click", () => run("update", updateButton));
  if (!localStorage.getItem("excelBackupPromptShown")) {
    localStorage.setItem("excelBackupPromptShown", "1");
    setTimeout(() => { if (confirm("هذه أول مرة تستخدم فيها حِسبة. هل تريد إنشاء نسخة Excel الآن؟")) saveButton.click(); }, 500);
  }
})();
