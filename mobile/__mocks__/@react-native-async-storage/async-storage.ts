const store: Record<string, string> = {};
const AsyncStorage = {
  getItem: jest.fn((key: string) => Promise.resolve(store[key] ?? null)),
  setItem: jest.fn((key: string, val: string) => { store[key] = val; return Promise.resolve(); }),
  removeItem: jest.fn((key: string) => { delete store[key]; return Promise.resolve(); }),
  clear: jest.fn(() => { Object.keys(store).forEach((k) => delete store[k]); return Promise.resolve(); }),
};
export default AsyncStorage;
