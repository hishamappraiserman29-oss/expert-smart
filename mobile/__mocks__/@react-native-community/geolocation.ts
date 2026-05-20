const Geolocation = {
  getCurrentPosition: jest.fn((success) => {
    success({
      coords: { latitude: 30.0444, longitude: 31.2357, accuracy: 10 }
    });
  }),
  watchPosition: jest.fn(() => 42),
  clearWatch: jest.fn(),
};
export default Geolocation;
