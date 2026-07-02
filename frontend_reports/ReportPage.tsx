// src/pages/ReportPage.tsx
import React, { useEffect, useState } from 'react';
import { reportApi } from '../services/api';

function ReportPage() {
  const [reports, setReports] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        // Запрос к сервису отчетов
        // session_id cookie отправится автоматически
        const response = await reportApi.get('/report', {
          params: {
            start_date: '2024-01-01',
            end_date: '2024-12-31',
            interval_type: 'month'
          }
        });
        setReports(response.data);
      } catch (error) {
        console.error('Failed to fetch reports:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Sensor Reports</h1>
      {reports && (
        <pre>{JSON.stringify(reports, null, 2)}</pre>
      )}
    </div>
  );
}