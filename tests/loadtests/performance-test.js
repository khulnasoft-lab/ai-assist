import http from 'k6/http';
import { sleep } from 'k6';
import { check } from 'k6';
export const options = {
  scenarios: {
    contacts: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 50 },
        { duration: '10m', target: 1000 },
        { duration: '10m', target: 0 },
      ],
      gracefulRampDown: '0s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<1000'], // 95 percent of response times must be below 500ms
  },
};


export default function () {
  const url = 'http://127.0.0.1:8080/v2/completions';
  const payload = JSON.stringify({
    prompt_version: 1,
    project_path: 'gitlab-org/modelops/applied-ml/review-recommender/pipeline-scheduler',
    project_id: 33191677,
    current_file: {
      file_name: 'test.py',
      content_above_cursor: 'def is_even(n: int) ->',
      content_below_cursor: ''
  }
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'vs-code-gitlab-workflow/3.60.0 VSCode/1.77.3 Node.js/16.14.2 (darwin; arm64)',
      'Authorization': 'Bearer glpat-dAnTszCXsE3xACa-nYE2'
    },
  };

  const res = http.post(url, payload, params);
  check(res, {
    'is status 200': (r) => r.status === 200,
  });
  sleep(5)
}