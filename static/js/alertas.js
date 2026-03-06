document.addEventListener('DOMContentLoaded', function() {
        
        // LÓGICA DE ALERTA INICIAL (solo si no hay mensajes flash)
        // Revisamos si hay mensajes flash pendientes. Si no hay, mostramos la bienvenida.
    const hasFlashedMessages = document.querySelector('.flashed-messages');
        if (!hasFlashedMessages) {
            Swal.fire({
            icon: 'info',
            title: '¡Bienvenido a la creación de Coladas!',
            text: 'Por favor, dar clic en Examinar para seleccionar archivo PDF y comenzar la conversión.',
            showConfirmButton: true,
            confirmButtonText: 'Ok'
        });
    }

    // alerta al momento de finalizar la funcion pdf_xls
    
    
});

// document.querySelector("form").addEventListener("submit", function() {
//     document.getElementById("pdfFile").value = "";
// });

document.addEventListener("DOMContentLoaded", function(){
    const campo = document.getElementById("pdfFile");
    if (campo) campo.value = "";
});