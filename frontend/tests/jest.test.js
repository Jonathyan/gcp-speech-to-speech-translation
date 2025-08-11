// Smoke test to validate Jest setup
describe('Jest Setup', () => {
  test('DOM environment works', () => {
    document.body.innerHTML = '<div id="test">Hello</div>';
    const element = document.getElementById('test');
    expect(element.textContent).toBe('Hello');
  });

  test('WebSocket mock available', () => {
    expect(global.WebSocket).toBeDefined();
    const ws = new WebSocket('ws://test');
    expect(ws.send).toBeDefined();
    expect(ws.close).toBeDefined();
  });

  test('Test utilities available', () => {
    expect(global.mockWebSocket).toBeDefined();
    const ws = global.mockWebSocket();
    expect(ws.send).toHaveBeenCalledTimes(0);
  });
});