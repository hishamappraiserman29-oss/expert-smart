let _counter = 0;
export const v4 = jest.fn(() => `mock-uuid-${++_counter}`);
export function resetCounter() { _counter = 0; }
