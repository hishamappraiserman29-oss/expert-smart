let _online = true;
let _listeners: ((s: any) => void)[] = [];

const NetInfo = {
  fetch: jest.fn().mockResolvedValue({ isConnected: true }),
  addEventListener: jest.fn((cb: (s: any) => void) => {
    _listeners.push(cb);
    return () => { _listeners = _listeners.filter((l) => l !== cb); };
  }),
  // Test helpers
  _setOnline(val: boolean) {
    _online = val;
    _listeners.forEach((l) => l({ isConnected: val }));
  },
};
export default NetInfo;
