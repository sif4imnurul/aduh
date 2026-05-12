const request = require('supertest');
const app = require('../app');

describe('Generated Transaction Tests', () => {

  it('POST /api/run-pipeline - Triggers the multi-agent code carbon analysis pipeline and streams execution logs via Server-Sent Events (SSE).', async () => {
    
    const response = await request(app)
      .post('/api/run-pipeline')
      .set('Content-Type', 'application/json')
      
      .send({

      });

    expect(response.statusCode).toBe(201);
  });
});
