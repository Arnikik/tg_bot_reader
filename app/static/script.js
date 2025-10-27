// === Telegram WebApp инициализация ===
if (window.Telegram && window.Telegram.WebApp) {
  Telegram.WebApp.expand();
  Telegram.WebApp.ready();
}

// === Получение user_id ===
function getUserId() {
  const urlParams = new URLSearchParams(window.location.search);
  const userIdFromUrl = urlParams.get('user_id');
  if (userIdFromUrl) return parseInt(userIdFromUrl);

  if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
    return window.Telegram.WebApp.initDataUnsafe.user.id;
  }

  return null;
}

// === Загрузка списка книг ===
async function loadBooks() {
  const content = document.getElementById('content');
  try {
    const userId = getUserId();
    let books = [];

    if (userId) {
      const response = await fetch(`/api/books?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        books = data.books || [];
      }
    }

    if (books.length === 0) {
      content.innerHTML = userId ? `
        <div class="no-books">
          <h3>📖 У вас пока нет книг</h3>
          <p>Используйте кнопку <b>📤 Загрузить книгу</b> в боте для добавления PDF файлов.</p>
          <p><small>Ваш ID: ${userId}</small></p>
        </div>
      ` : `
        <div class="no-books">
          <h3>🔐 Требуется авторизация</h3>
          <p>Откройте это приложение через Telegram бота для доступа к вашим книгам.</p>
        </div>
      `;
    } else {
      content.innerHTML = `
        <ul class="book-list">
          ${books.map(book => `
            <li>
              <a href="/view/${encodeURIComponent(book.name)}?user_id=${userId}${book.file_id ? '&file_id=' + book.file_id : ''}" class="book-item">
                📄 ${book.name}
              </a>
            </li>
          `).join('')}
        </ul>
        <div style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
          Ваш ID: ${userId}
        </div>
      `;
    }
  } catch (err) {
    console.error('Ошибка загрузки книг:', err);
    content.innerHTML = `
      <div class="no-books">
        <h3>❌ Ошибка загрузки</h3>
        <p>Не удалось загрузить список книг. Попробуйте позже.</p>
      </div>
    `;
  }
}

// === Запуск ===
window.addEventListener('DOMContentLoaded', loadBooks);
