// IndexedDB の最小ラッパー（依存ライブラリなし）。端末内の永続保存に使う。
// ストア "kv" に key → JSON 値を入れる。IndexedDB が使えない環境（古いブラウザ・テスト）ではメモリで代用する。

const DB_NAME = 'aqros'
const STORE = 'kv'
let dbp: Promise<IDBDatabase> | null = null
const mem = new Map<string, unknown>()

function hasIdb() { return typeof indexedDB !== 'undefined' }

function open(): Promise<IDBDatabase> {
  if (!dbp) {
    dbp = new Promise((resolve, reject) => {
      const r = indexedDB.open(DB_NAME, 1)
      r.onupgradeneeded = () => { if (!r.result.objectStoreNames.contains(STORE)) r.result.createObjectStore(STORE) }
      r.onsuccess = () => resolve(r.result)
      r.onerror = () => reject(r.error)
    })
  }
  return dbp
}

function tx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T> | void): Promise<T | undefined> {
  return open().then((db) => new Promise<T | undefined>((resolve, reject) => {
    const t = db.transaction(STORE, mode)
    const req = fn(t.objectStore(STORE))
    t.oncomplete = () => resolve(req ? (req as IDBRequest<T>).result : undefined)
    t.onerror = () => reject(t.error)
    t.onabort = () => reject(t.error || new Error('IndexedDB transaction aborted（容量不足の可能性）'))
  }))
}

export const kv = {
  async get<T>(key: string): Promise<T | undefined> {
    if (!hasIdb()) return mem.get(key) as T | undefined
    return tx<T>('readonly', (s) => s.get(key) as IDBRequest<T>)
  },
  async set(key: string, value: unknown): Promise<void> {
    if (!hasIdb()) { mem.set(key, structuredClone(value)); return }
    await tx('readwrite', (s) => { s.put(value, key) })
  },
  async del(key: string): Promise<void> {
    if (!hasIdb()) { mem.delete(key); return }
    await tx('readwrite', (s) => { s.delete(key) })
  },
  async keys(prefix = ''): Promise<string[]> {
    const all = !hasIdb() ? [...mem.keys()] : ((await tx<IDBValidKey[]>('readonly', (s) => s.getAllKeys())) || []).map(String)
    return all.filter((k) => k.startsWith(prefix)).sort()
  },
  async entries(prefix = ''): Promise<[string, unknown][]> {
    const ks = await this.keys(prefix)
    return Promise.all(ks.map(async (k) => [k, await this.get(k)] as [string, unknown]))
  },
  async clear(): Promise<void> {
    if (!hasIdb()) { mem.clear(); return }
    await tx('readwrite', (s) => { s.clear() })
  },
}

/** ブラウザに「消さないで」と依頼する（iOS/Android とも許可は保証されない） */
export async function requestPersist(): Promise<boolean | null> {
  try {
    if (!navigator.storage?.persist) return null
    if (await navigator.storage.persisted()) return true
    return await navigator.storage.persist()
  } catch { return null }
}

export async function storageEstimate(): Promise<{ usage: number; quota: number } | null> {
  try { const e = await navigator.storage.estimate(); return { usage: e.usage || 0, quota: e.quota || 0 } } catch { return null }
}
