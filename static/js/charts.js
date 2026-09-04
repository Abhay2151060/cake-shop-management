// Analytics & Charts Loader
document.addEventListener('DOMContentLoaded', () => {
  const salesCanvas = document.getElementById('salesTrendChart');
  const paymentCanvas = document.getElementById('paymentSplitChart');
  const topProductsCanvas = document.getElementById('topProductsChart');

  if (salesCanvas || paymentCanvas || topProductsCanvas) {
    loadChartData();
  }
});

async function loadChartData() {
  try {
    const res = await fetch('/api/analytics/charts');
    const data = await res.json();

    // 1. Sales Trend Line Chart
    const salesCanvas = document.getElementById('salesTrendChart');
    if (salesCanvas && data.sales_trend) {
      new Chart(salesCanvas, {
        type: 'line',
        data: {
          labels: data.sales_trend.labels,
          datasets: [{
            label: 'Sales (₹)',
            data: data.sales_trend.sales,
            borderColor: '#e11d48',
            backgroundColor: 'rgba(225, 29, 72, 0.08)',
            fill: true,
            tension: 0.35,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: '#e11d48',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return ' Sales: ₹' + context.raw.toLocaleString();
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                callback: function(value) { return '₹' + value; }
              }
            }
          }
        }
      });
    }

    // 2. Payment Split Doughnut Chart
    const paymentCanvas = document.getElementById('paymentSplitChart');
    if (paymentCanvas && data.payment_split) {
      new Chart(paymentCanvas, {
        type: 'doughnut',
        data: {
          labels: data.payment_split.labels,
          datasets: [{
            data: data.payment_split.values,
            backgroundColor: ['#10b981', '#0284c7', '#f59e0b'],
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return ' ' + context.label + ': ₹' + context.raw.toLocaleString();
                }
              }
            }
          }
        }
      });
    }

    // 3. Top Products Bar Chart
    const topProductsCanvas = document.getElementById('topProductsChart');
    if (topProductsCanvas && data.top_products) {
      new Chart(topProductsCanvas, {
        type: 'bar',
        data: {
          labels: data.top_products.labels,
          datasets: [{
            label: 'Qty Sold',
            data: data.top_products.quantities,
            backgroundColor: 'rgba(225, 29, 72, 0.85)',
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1 }
            }
          }
        }
      });
    }

  } catch (err) {
    console.error("Error loading charts:", err);
  }
}
