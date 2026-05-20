const Voice = {
  start: jest.fn().mockResolvedValue(undefined),
  stop: jest.fn().mockResolvedValue({
    uri: 'file://recording.m4a',
    value: ['Property in good condition, three bedrooms'],
  }),
  destroy: jest.fn().mockResolvedValue(undefined),
  removeAllListeners: jest.fn(),
};
export default Voice;
