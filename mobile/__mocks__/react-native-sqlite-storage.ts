/**
 * In-memory SQLite mock for Jest.
 * Handles all SQL patterns used by OfflineStorage.ts.
 */

type Row = Record<string, any>;
type Tables = Record<string, Row[]>;

class MockRows {
  private _data: Row[];
  constructor(data: Row[]) { this._data = data; }
  get length() { return this._data.length; }
  item(i: number) { return this._data[i]; }
}

class MockResultSet {
  rows: MockRows;
  constructor(data: Row[]) { this.rows = new MockRows(data); }
}

class MockSQLiteDatabase {
  private tables: Tables = {};

  async executeSql(sql: string, params: any[] = []): Promise<[MockResultSet]> {
    const s = sql.trim();
    const upper = s.toUpperCase();

    // ── CREATE TABLE ──────────────────────────────────────────────────────
    if (/^CREATE TABLE/i.test(s)) {
      const m = s.match(/CREATE TABLE IF NOT EXISTS (\w+)/i);
      if (m && !this.tables[m[1]]) this.tables[m[1]] = [];
      return [new MockResultSet([])];
    }

    // ── CREATE INDEX ──────────────────────────────────────────────────────
    if (/^CREATE INDEX/i.test(s)) return [new MockResultSet([])];

    // ── INSERT INTO ───────────────────────────────────────────────────────
    if (/^INSERT INTO/i.test(s)) {
      const tableM = s.match(/INSERT INTO (\w+)/i);
      if (!tableM) return [new MockResultSet([])];
      const table = tableM[1];
      const colsM = s.match(/\(([^)]+)\)\s+VALUES/i);
      if (!colsM) return [new MockResultSet([])];
      const cols = colsM[1].split(',').map((c) => c.trim());
      const row: Row = { retries: 0 };  // Default for all tables
      cols.forEach((col, i) => { row[col] = params[i]; });
      if (!this.tables[table]) this.tables[table] = [];
      this.tables[table].push(row);
      return [new MockResultSet([])];
    }

    // ── UPDATE ────────────────────────────────────────────────────────────
    if (/^UPDATE/i.test(s)) {
      const tableM = s.match(/UPDATE (\w+)/i);
      if (!tableM) return [new MockResultSet([])];
      const table = tableM[1];
      const rows = this.tables[table] || [];

      // Special case: retries = retries + 1
      if (/retries\s*=\s*retries\s*\+\s*1/i.test(s)) {
        const idParam = params[0];
        rows.forEach((r) => { if (r.id === idParam) r.retries = (r.retries || 0) + 1; });
        return [new MockResultSet([])];
      }

      // Generic: SET ... WHERE ...
      const setM = s.match(/SET\s+([\s\S]+?)\s+WHERE\s+([\s\S]+)/);
      if (!setM) return [new MockResultSet([])];
      const [, setPart, wherePart] = setM;

      // Parse SET assignments: col = 'literal' or col = ?
      let pIdx = 0;
      const setOps: Array<{ col: string; val: any }> = [];
      for (const raw of setPart.split(',')) {
        const a = raw.trim();
        const litM = a.match(/^(\w+)\s*=\s*'([^']*)'/);
        const pM = a.match(/^(\w+)\s*=\s*\?/);
        if (litM) {
          setOps.push({ col: litM[1], val: litM[2] });
        } else if (pM) {
          setOps.push({ col: pM[1], val: params[pIdx++] });
        }
      }

      // Parse WHERE col = ? conditions
      const whereMatches = [...wherePart.matchAll(/(\w+)\s*=\s*\?/gi)];
      rows.forEach((row) => {
        const hit = whereMatches.every((m, i) =>
          String(row[m[1]]) === String(params[pIdx + i])
        );
        if (hit) setOps.forEach(({ col, val }) => { row[col] = val; });
      });

      return [new MockResultSet([])];
    }

    // ── SELECT COUNT(*) ───────────────────────────────────────────────────
    if (/SELECT\s+COUNT/i.test(s)) {
      const tableM = s.match(/FROM\s+(\w+)/i);
      if (!tableM) return [new MockResultSet([{ count: 0 }])];
      const table = tableM[1];
      let rows = this.tables[table] || [];

      const whereM = s.match(/WHERE\s+(.+)/i);
      if (whereM) {
        const cond = whereM[1].trim();
        const litM = cond.match(/(\w+)\s*=\s*'([^']+)'/i);
        const pM = cond.match(/(\w+)\s*=\s*\?/i);
        if (litM) {
          rows = rows.filter((r) => String(r[litM[1]]) === litM[2]);
        } else if (pM) {
          rows = rows.filter((r) => String(r[pM[1]]) === String(params[0]));
        }
      }
      return [new MockResultSet([{ count: rows.length }])];
    }

    // ── SELECT * ─────────────────────────────────────────────────────────
    if (/^SELECT/i.test(s)) {
      const tableM = s.match(/FROM\s+(\w+)/i);
      if (!tableM) return [new MockResultSet([])];
      const table = tableM[1];
      let rows = [...(this.tables[table] || [])];

      const whereM = s.match(/WHERE\s+(.+?)(?:\s+ORDER|\s+LIMIT|$)/i);
      if (whereM) {
        const conditions = whereM[1].split(/\s+AND\s+/i);
        let pIdx2 = 0;
        conditions.forEach((cond) => {
          const litM = cond.match(/(\w+)\s*=\s*'([^']+)'/i);
          const pM = cond.match(/(\w+)\s*=\s*\?/i);
          if (litM) {
            rows = rows.filter((r) => String(r[litM[1]]) === litM[2]);
          } else if (pM) {
            const v = params[pIdx2++];
            rows = rows.filter((r) => String(r[pM[1]]) === String(v));
          }
        });
      }

      if (/ORDER BY.*DESC/i.test(s)) {
        const orderM = s.match(/ORDER BY\s+(\w+)\s+DESC/i);
        if (orderM) {
          const col = orderM[1];
          rows.sort((a, b) => (a[col] > b[col] ? -1 : 1));
        }
      }

      return [new MockResultSet(rows)];
    }

    return [new MockResultSet([])];
  }

  _getTable(name: string): Row[] { return this.tables[name] || []; }
  _clearAll(): void { this.tables = {}; }
}

const _db = new MockSQLiteDatabase();

const SQLite = {
  openDatabase: jest.fn().mockResolvedValue(_db),
  _db,
};

export default SQLite;
export { MockSQLiteDatabase };
