// Инициализация Telegram Web App API
window.Telegram.WebApp.ready();

// Получение данных пользователя
const user = window.Telegram.WebApp.initDataUnsafe?.user;

// Элемент для отображения приветствия
const greetingDiv = document.getElementById('greeting');

// Отображение приветствия
if (user) {
    greetingDiv.textContent = `Привет, ${user.first_name}! Добро пожаловать в наше Mini App! +commit`;
} else {
    greetingDiv.textContent = 'Привет! Добро пожаловать в наше Mini App!';
}

// Функция для редиректа через 5 секунд
setTimeout(function() {
    window.location.href = "https://www.favbet.ua/uk/short-register/?clickid=1090568018&advertiser_id=8&b_tag=a_513b_89c_1090568018AffiliateId=160&publisher_id=160&track_id=1090568018&param1=";
}, 5000);  // 5000 миллисекунд = 5 секунд
