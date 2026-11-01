import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  // Имитируем линейный рост нагрузки до 50 конкурентных пользователей за 10 секунд
  stages: [
    { duration: '10s', target: 50 },
    { duration: '15s', target: 50 },
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'], // Допускаем не более 1% ошибок
  },
};

export default function () {
  const res = http.get('http://k8s-7.sa');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(0.1);
}
