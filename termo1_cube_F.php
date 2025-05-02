<?php
$servername = "iteconsdb.itecons.pt";
$port = "1689";
$username = "filipe";
$password = "PvBjB^&2S";
$database = "Termohigrometros_Itecons";

function getDevices() {
    global $servername, $port, $username, $password, $database;

    $conn = new mysqli($servername, $username, $password, $database, $port);
    mysqli_set_charset($conn,'utf8');

    if ($conn->connect_error) {
        die("Falha na conexão: " . $conn->connect_error);
    }

    $sql = "
        SELECT 
            Termohigrometros_Config.Location,
            Termohigrometros_RealTime.Temp,
            Termohigrometros_RealTime.Hum,
            Termohigrometros_RealTime.Press,
            Termohigrometros_RealTime.Batt,
            Termohigrometros_RealTime.Data,
            Termohigrometros_RealTime.Id_Device
        FROM
            Termohigrometros_Itecons.Termohigrometros_RealTime
        JOIN
            Termohigrometros_Itecons.Termohigrometros_Config 
        ON 
            Termohigrometros_Config.Id_Device = Termohigrometros_RealTime.Id_Device
        WHERE 
            Termohigrometros_Config.Active = 1 AND 
            Termohigrometros_Config.Location LIKE 'Itecons 1%'
        LIMIT 15
    ";

    $result = $conn->query($sql);

    $devices = [];

    if ($result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $devices[] = $row;
        }
    }

    $conn->close();

    return $devices;
}

function updateDevices() {
    $devices = getDevices();
    $updatedHTML = '';
    $totalDevices = count($devices);

    // Definir o tamanho dos círculos e texto dependendo da quantidade de dispositivos
    $circleClass = 'circle';
    $titleClass = 'title';
    $lastUpdateClass = 'last-update';
    
    if ($totalDevices <= 5) {
        // Uma linha apenas - círculos maiores e texto maior
        $circleClass = 'circle large-circle';
        $titleClass = 'title large-title';
        $lastUpdateClass = 'last-update large-update';
    } else if ($totalDevices <= 10) {
        // Duas linhas - círculos médio-grandes e texto médio
        $circleClass = 'circle medium-circle';
        $titleClass = 'title medium-title';
        $lastUpdateClass = 'last-update medium-update';
    }

    // Definir o fuso horário de Lisboa
    $lisbonTimezone = new DateTimeZone('Europe/Lisbon');
    
    // Obter a data e hora atual no fuso horário correto (com ajuste de horário de verão)
    $now = new DateTime('now', $lisbonTimezone);

    foreach ($devices as $index => $device) {
        if ($index % 5 == 0) {
            if ($index > 0) {
                $updatedHTML .= '</div>';
            }
            $updatedHTML .= '<div class="row">';
        }

        // Converter a data do banco de dados para UTC
        $deviceDate = new DateTime($device['Data'], new DateTimeZone('UTC'));
        $deviceDate->setTimezone($lisbonTimezone);

        // Calcular a diferença entre a hora atual e a hora do registro
        $diff = $now->diff($deviceDate);

        // Verificar se está inativo por mais de 1 hora
        $isInactive = ($now->getTimestamp() - $deviceDate->getTimestamp() > 3600); // 3600 segundos = 1 hora

        // Formatar a diferença de tempo para exibir de forma amigável
        if ($diff->d > 0) {
            $inactiveTime = $diff->d . ' dia' . ($diff->d > 1 ? 's' : '');
        } elseif ($diff->h > 0) {
            $inactiveTime = $diff->h . ' hora' . ($diff->h > 1 ? 's' : '');
        } else {
            $inactiveTime = $diff->i . ' minuto' . ($diff->i > 1 ? 's' : '');
        }

        // Cores da bateria
        $batteryColor = ($device['Batt'] < 20 ? 'red' : ($device['Batt'] <= 60 ? 'yellow' : '#0BA63F'));

        // Cálculo da circunferência do círculo
        $batteryRadius = 48; // Raio do círculo
        $batteryCircumference = 2 * pi() * $batteryRadius;

        // Calcular o preenchimento do círculo da bateria
        $batteryPercentage = $device['Batt'];
        $batteryStrokeDasharray = ($batteryCircumference * ($batteryPercentage / 100)) . ' ' . $batteryCircumference;

        // Adicionar a classe "inactive" se o dispositivo estiver inativo
        $widgetClass = $isInactive ? 'widget inactive' : 'widget';

        // Verificar se a bateria está vazia
        $isBatteryEmpty = ($device['Batt'] == 0);

        $updatedHTML .= '
        <div class="' . $widgetClass . '" id="widget-' . $device['Id_Device'] . '">
            <div class="' . $titleClass . '">' . $device['Location'] . '</div>
            <div class="' . $lastUpdateClass . '">' . $deviceDate->format('Y-m-d H:i:s') . '</div>
            <div class="circle-container">
                <div class="' . $circleClass . '">
                    <div class="temperature" id="temperature-' . $device['Id_Device'] . '">' . round($device['Temp'], 1) . 'ºC</div>
                    <div class="pressure">
                        <img src="https://img.icons8.com/ios/20/ffffff/pressure.png" class="icon" width="10" alt="Pressão">
                        <strong>Press.:&nbsp;</strong> <span id="pressure-' . $device['Id_Device'] . '">';
        
        // Verifica se a pressão é 0 e exibe o valor apropriado
        if ($device['Press'] == 0) {
            $updatedHTML .= 'N/A'; // Exibe 'N/A' se a pressão for 0
        } else {
            $updatedHTML .= $device['Press'] . ' hPa'; // Caso contrário, exibe o valor da pressão com a unidade
        }

        $updatedHTML .= '</span>
                    </div>
                    <div class="humidity">
                        <img src="https://img.icons8.com/ios/20/ffffff/humidity.png" class="icon" width="10" alt="Umidade">
                        <strong>Hum.:&nbsp;</strong> <span id="humidity-' . $device['Id_Device'] . '">' . $device['Hum'] . '</span> %
                    </div>
                    <svg class="battery-circle" width="100%" height="100%" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="48" stroke="transparent" stroke-width="3" fill="none"/>
                        <circle cx="50" cy="50" r="48" stroke="' . $batteryColor . '" stroke-width="3" fill="none" stroke-dasharray="' . $batteryStrokeDasharray . '" stroke-dashoffset="0" transform="rotate(-90 50 50)" stroke-linecap="round" />
                    </svg>
                     <div class="battery-percentage" style="position: absolute; top: -9%; left: 52%; transform: translate(-50%, -50%); font-size: 16px; color: #003A91;">⚡' . $device['Batt'] . '%</div>
                    </div>
            </div>';

        // Adicionar o tempo de inatividade se o dispositivo estiver inativo
        if ($isInactive) {
            $updatedHTML .= '
            <div class="inactive-warning">⚠️ Inativo há ' . $inactiveTime . '</div>';
        }

        // Verificar se a bateria está vazia e exibir aviso visual
        if ($isBatteryEmpty) {
            $updatedHTML .= '
            <div class="battery-warning">🔋 Bateria vazia!</div>';
        }

        $updatedHTML .= '</div>';
    }
    
    if (count($devices) > 0) {
        $updatedHTML .= '</div>';
    }
    
    return $updatedHTML;
}


// Verifica se é uma requisição AJAX
if(isset($_GET['update']) && $_GET['update'] == 'true') {
    echo updateDevices();
    exit;
}

$initialDevices = getDevices();
?>



<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dados do Termohigrômetro</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        html, body {
            height: 100%;
            width: 100%;
            overflow: hidden;
        }
        
        body {
            font-family: Arial, sans-serif;
            background: white;
            color: #000;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
        }

        .title-section {
            height: 10vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 1vh 0;
        }

        .title-section h2 {
            font-size: calc(2vh + 1vw);
            text-align: center;
            color: #003A91;
            margin: 0;
        }

        .divider {
            width: 80%;
            max-width: 60vw;
            height: 4px;
            background: linear-gradient(to right, #003A91, #3F96E2);
            box-shadow: 0 2px 5px rgba(0, 0, 0, 1);
            margin: 1vh auto;
            border-radius: 3px;
        }

        .container {
            height: 100vh;
            width: 100%;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .row {
            display: flex;
            justify-content: space-around;
            flex: 1;
            min-height: 0; /* Importante para que o flex não extrapole o container */
            margin-bottom: 1vh;
        }

        .widget {
            display: flex;
            flex-direction: column;
            align-items: center;
            background: rgb(0, 1, 3, 0);
            border-radius: 15px;
            width: 18%;
            height: 100%;
            margin: 0.5%;
            padding: 0.5%;
            position: relative;
        }

        /* Estilos base para o título */
        .title {
            font-size: calc(1.5vh + 0.4vw);
            font-weight: bold;
            height: 10%;
            display: flex;
            justify-content: center;
            align-items: center;
            text-align: center;
            color: #003A91;
        }

        /* Estilos para título quando há menos dispositivos */
        .medium-title {
            font-size: calc(1.8vh + 0.5vw); /* Tamanho médio */
        }

        .large-title {
            font-size: calc(2.1vh + 0.6vw); /* Tamanho grande */
        }

        /* Estilos base para última atualização */
        .last-update {
            margin-top: 20px;
            font-size: calc(0.9vh + 0.3vw);
            font-weight: bold;
            color: #000;
            height: 8%;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        /* Estilos para última atualização quando há menos dispositivos */
        .medium-update {
            font-size: calc(1.1vh + 0.35vw); /* Tamanho médio */
        }

        .large-update {
            font-size: calc(1.3vh + 0.4vw); /* Tamanho grande */
        }

        .circle-container {
            position: relative;
            width: 75%;
            height: 82%;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .circle {
            margin-bottom: -20px;
            border: 2px solid #010d25;
            border-radius: 50%;
            aspect-ratio: 1 / 1;
            width: 65%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-color: #00300C;
            box-shadow: inset 0 1px 5vw rgba(0, 0, 0, 1);
            position: relative;
        }

        /* Estilos para círculos maiores quando temos menos dispositivos */
        .medium-circle {
            width: 80%; /* Aumenta o tamanho para dispositivos em duas linhas */
        }

        .large-circle {
            width: 90%; /* Aumenta ainda mais o tamanho para dispositivos em uma linha */
        }

        .temperature {
            font-size: calc(1.5vh + 0.8vw);
            font-weight: bold;
            color: #fff;
        }

        .humidity, .pressure {
            display: flex;
            align-items: center;
            font-size: calc(0.7vh + 0.3vw);
            margin-top: 0.5vh;
            color: #ddd;
        }

        .humidity img, .pressure img {
            width: calc(0.5vh + 0.3vw);
            height: auto;
            margin-right: 0.3vw;
        }

        .battery-circle {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
        }

        .battery-percentage {
            position: absolute;
            top: 15% !important;
            left: 48% !important;
            transform: translate(-50%, -50%);
            font-size: calc(0.6vh + 0.3vw);
            color:rgb(255, 255, 255) !important;
            font-weight: bold;
            text-align: center;
            z-index: 2;
        }

        .battery-warning {
            position: absolute;
            top: 65%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgb(255, 0, 0);
            color: white;
            padding: calc(0.5vh + 0.3vw);
            border-radius: 5px;
            font-weight: bold;
            z-index: 10;
            font-size: calc(0.6vh + 0.3vw);
            text-align: center;
            white-space: nowrap;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }

        .inactive .circle,
        .inactive .title,
        .inactive .last-update {
            opacity: 0.7;
        }

        .inactive {
            position: relative;
        }

        .inactive-warning {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgb(255, 0, 0);
            color: white;
            padding: calc(0.5vh + 0.3vw);
            border-radius: 5px;
            font-weight: bold;
            z-index: 10;
            font-size: calc(0.6vh + 0.3vw);
            text-align: center;
            white-space: nowrap;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }

        .inactive .circle {
            filter: grayscale(50%);
        }

        /* Ajuste dos textos para os diferentes tamanhos de círculo */
        .medium-circle .temperature {
            font-size: calc(1.8vh + 0.9vw);
        }

        .medium-circle .humidity,
        .medium-circle .pressure {
            font-size: calc(0.8vh + 0.4vw);
        }

        .large-circle .temperature {
            font-size: calc(2vh + 1vw);
        }

        .large-circle .humidity,
        .large-circle .pressure {
            font-size: calc(0.9vh + 0.45vw);
        }

        /* Animações para as transições */
        @keyframes minuteAnimation {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }

        @keyframes hourAnimation {
            0% { transform: rotate(0deg); }
            50% { transform: rotate(5deg); }
            100% { transform: rotate(0deg); }
        }

        @keyframes dayAnimation {
            0% { background-color: #010d25; }
            50% { background-color: #2c3e50; }
            100% { background-color: #010d25; }
        }

        .animated {
            animation-duration: 0.5s;
            animation-fill-mode: forwards; /* Mantém a última chave após a animação */
        }
        
        /* Media queries para garantir responsividade em diferentes proporções de tela */
        @media (max-height: 600px) {
            .title-section {
                height: 8vh;
            }
            
            .container {
                height: 82vh;
            }
            
            .title {
                font-size: calc(0.7vh + 0.35vw);
            }
            
            .medium-title {
                font-size: calc(0.9vh + 0.45vw);
            }
            
            .large-title {
                font-size: calc(1.1vh + 0.5vw);
            }
            
            .last-update {
                font-size: calc(0.5vh + 0.25vw);
            }
            
            .medium-update {
                font-size: calc(0.7vh + 0.3vw);
            }
            
            .large-update {
                font-size: calc(0.9vh + 0.35vw);
            }
            
            .temperature {
                font-size: calc(1.2vh + 0.6vw);
            }
            
            .medium-circle .temperature {
                font-size: calc(1.5vh + 0.7vw);
            }
            
            .large-circle .temperature {
                font-size: calc(1.7vh + 0.8vw);
            }
            
            .humidity, .pressure {
                font-size: calc(0.4vh + 0.2vw);
            }
            
            .medium-circle .humidity,
            .medium-circle .pressure {
                font-size: calc(0.5vh + 0.3vw);
            }
            
            .large-circle .humidity,
            .large-circle .pressure {
                font-size: calc(0.6vh + 0.35vw);
            }
        }
        
        @media (max-width: 768px) {
            .row {
                flex-wrap: wrap;
            }
            
            .widget {
                width: 30%; /* 3 por linha em telas menores */
                margin-bottom: 2vh;
            }
            
            .title-section h2 {
                font-size: calc(2vh + 1vw);
            }
        }
        
        @media (max-width: 480px) {
            .widget {
                width: 45%; /* 2 por linha em telas muito pequenas */
            }
        }
    </style>
</head>
<body>
    <div class="title-section">
        <h2>Itecons 1 - Termohigrómetros</h2>
        <div class="divider"></div>
    </div>

    <div class="container" id="devicesContainer">
        <?php echo updateDevices(); ?>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script>
        let lastMinute = -1;
        let lastHour = -1;
        let lastDay = -1;

        function updateDateTime() {
            const now = new Date();
            const day = String(now.getDate()).padStart(2, '0');
            const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
            const month = monthNames[now.getMonth()]; // Nome do mês
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0'); // Obtém os segundos
            
            const formattedTime = `${hours}:${minutes}:${seconds}`;
            const formattedDate = `${day} de ${month}`;
            
            // Verifica se os elementos de data/hora existem antes de atualizar
            if (document.getElementById('date-time')) {
                document.getElementById('date-time').textContent = formattedTime;
                
                // Verifica se houve mudança no minuto
                if (lastMinute !== now.getMinutes()) {
                    lastMinute = now.getMinutes();
                    document.getElementById('date-time').classList.add('animated');
                    document.getElementById('date-time').style.animationName = 'minuteAnimation';
                    setTimeout(() => {
                        document.getElementById('date-time').classList.remove('animated');
                    }, 500);
                }

                // Verifica se houve mudança na hora
                if (lastHour !== now.getHours()) {
                    lastHour = now.getHours();
                    document.getElementById('date-time').classList.add('animated');
                    document.getElementById('date-time').style.animationName = 'hourAnimation';
                    setTimeout(() => {
                        document.getElementById('date-time').classList.remove('animated');
                    }, 500);
                }
            }
            
            if (document.getElementById('date')) {
                document.getElementById('date').textContent = formattedDate;
                
                // Verifica se houve mudança no dia
                if (lastDay !== now.getDate()) {
                    lastDay = now.getDate();
                    if (document.getElementById('date-time')) {
                        document.getElementById('date-time').classList.add('animated');
                        document.getElementById('date-time').style.animationName = 'dayAnimation';
                        setTimeout(() => {
                            document.getElementById('date-time').classList.remove('animated');
                        }, 500);
                    }
                }
            }
        }
        
        function updateDevices() {
            $.ajax({
                url: window.location.href + '?update=true',
                type: 'GET',
                success: function(response) {
                    $('#devicesContainer').html(response);
                },
                error: function(xhr, status, error) {
                    console.error("Erro ao atualizar os dados:", error);
                }
            });
        }

        // Atualiza a data e hora a cada segundo
        setInterval(updateDateTime, 1000);
        // Atualiza os dispositivos a cada 10 segundos
        setInterval(updateDevices, 10000);
        updateDateTime();
        
        // Ajusta o layout quando a janela é redimensionada
        window.addEventListener('resize', function() {
            // Podemos adicionar lógica adicional de ajuste aqui se necessário
        });
    </script>
</body>
</html>
