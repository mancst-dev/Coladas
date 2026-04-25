import camelot
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import pandas as pd
import os
import sys
from camelot.core import TableList
from flask import Flask, request, jsonify, redirect, url_for, send_file, render_template, flash, after_this_request, make_response, session
from werkzeug.utils import secure_filename
import time #generar archivos unicos
import shutil #limpiar info contenida en carpetas

#carpeta para archivos pdfs subidos
SUBIDA_ARCHIVOS = 'subida'
#carpta para resultados xlsx
DESCARGA_ARCHIVOS = 'descarga'
EXTENSIONES = {'pdf'}

app = Flask(__name__)
app.config['SUBIDA_ARCHIVOS'] = SUBIDA_ARCHIVOS
app.config['DESCARGA_ARCHIVOS'] = DESCARGA_ARCHIVOS

#dado el caso que llegue a utilizar flash messages
app.secret_key = 'super_secreto_para_flash'

#aseguro que las carpetas existan
os.makedirs(SUBIDA_ARCHIVOS, exist_ok=True)
os.makedirs(DESCARGA_ARCHIVOS,exist_ok=True)

#verificacion de extension

def archivo_permitido(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in EXTENSIONES

#funcion central
def pdf_xls(archivoPdf_ruta, excelGenerado_ruta):

    print(f"Extrayendo tablas de: {archivoPdf_ruta}")

    try:
        #extraertabla usando el flavor lattice con bordes
        tables = camelot.read_pdf(archivoPdf_ruta, pages="all", flavor="lattice")
        if not isinstance(tables, TableList) or tables.n == 0:
            #si 'lattice' no encuentra nada, con 'stream' sin bordes
            #tables = camelot.read_pdf(archivoPdf_ruta, pages="all", flavor="stream")
            #if tables.n == 0:
            raise ValueError(f"No se pudo extraer ninguna tabla del archivo pdf '{archivoPdf_ruta}'.")
        print(f"Extraccion exitosa. Se encontraron {tables.n} tabla(s).")

    #excepciones de extraccion
    except FileNotFoundError:
        return False, f"Error: el archivo pdf '{archivoPdf_ruta}' no se encontró."
    except camelot.errors.PDFNotReadableError:
        return False, f"Error: el archivo pdf '{archivoPdf_ruta} está corrupto o protegido.'"
    except Exception as e:
        return False, f"Error inesperado durante la extracción: {e}"
    
    #guardado de archivo de excel
    print(f"intentando guardar {tables.n} tabla(s) en el archivo: {excelGenerado_ruta}...")
    try:
        tables.export(excelGenerado_ruta, f="excel")

        if not os.path.exists(excelGenerado_ruta):
            raise IOError(f"El archivo de excel '{excelGenerado_ruta}' no fue creado despues de la exportacion")
        
        print(f"Exito: tablas extraidas y guardadas en '{excelGenerado_ruta}'.")
        return True, excelGenerado_ruta
    
    except IOError as e:
        return False, f"Error de guardado: problema al escribir el archivo '{excelGenerado_ruta}'. Detalle: {e}"
    
    except Exception as e:
        return False, f"Error inesperado durante el guardado: {e}"
    

#rutas de Flask
#muestra el formulario de subida (ruta que usaría el usuario)
#nota: la ruta real en el servidor será solo /
# @app.route('/')
@app.route('/')
def index():
    # HTML estáen 'templates/pdf_to_xls.html'
    # session.pop('limpiar_input', None) # declarar el input para limpiarlo
    return render_template('Index.html')

#Muestra el formulario de subida pdf a xlsx(ruta corregida)
@app.route('/upload')
def frm_subida():
    # HTMLestá en 'templates/pdf_to_xls.html'
    return render_template('pdf_to_xls.html')

# Procesa subida del archivo. ruta es llamada action del formulario.
@app.route('/convert', methods=['POST'])
def convertir_archivo():
    #verificar si el campo 'pdfFile' está ensolicitud
    if 'pdfFile' not in request.files:
        flash('No se encontró el campo de archivo en el formulario.', 'error')
        return redirect(url_for('index')) # Redirigir a 'index'

    file = request.files['pdfFile']

    #verificar si el usuario no selecciono archivo
    if file.filename == '':
        flash('Error: No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('index')) # Redirigir a 'index'

    if file and archivo_permitido(file.filename):
    #1 guardar pdf temporalmente
        archivoOriginal = secure_filename(file.filename)
        timestamp = int(time.time())

        nom_archivo_pdf = f"{timestamp}_{archivoOriginal}"
        ruta_pdf = os.path.join(app.config['SUBIDA_ARCHIVOS'], nom_archivo_pdf)
        file.save(ruta_pdf)

        #2 definir ruta de salida xlsx
        nom_archivo_base = os.path.splitext(archivoOriginal)[0]
        nom_archivo_salida = f"{nom_archivo_base}_extracted_{timestamp}.xlsx"
        ruta_salida = os.path.join(app.config['DESCARGA_ARCHIVOS'], nom_archivo_salida)

        #3 convertir
        success, result = pdf_xls(ruta_pdf, ruta_salida)

        #4 limpieza y respuesta
        try:
            os.remove(ruta_pdf) #eliminar el pdf subido después del procesamiento
        except OSError as e:
            print(f"error al limpiar el pdf temporal: {e}")

        if success:
            flash(f'¡Conversión exitosa! El archivo "{nom_archivo_base}.xlsx" se está descargando.', 'success')
            
            #exitosa, redirige adescarga
            # session['limpiar_input']=True #declaramos que el input se limpie
            return redirect(url_for('archivo_descarga', filename=nom_archivo_salida, original_name=nom_archivo_base))
        else:
            #si falla
            flash(f"Error en la conversión: {result}", 'error')
        return redirect(url_for('index'))
    else:
        flash('Error: tipo de archivo no permitido. solo se aceptan pdfs.', 'error')
    return redirect(url_for('index'))
    

#ruta de descarga
@app.route('/download/<filename>')
def archivo_descarga(filename):
    # Se añade original_name como argumento para poder flashear el nombre original después de la descarga
    original_name = request.args.get('original_name', 'archivo')
    ruta_archivo = os.path.join(app.config['DESCARGA_ARCHIVOS'], filename)

    if os.path.exists(ruta_archivo):
        print(f"Enviando para descarga: {ruta_archivo}")

        # Obtenemos el nombre limpio para el usuario
        nombre_descarga = original_name + '.xlsx'

        try:
            # 1. Usamos send_file para crear la respuesta de descarga
            response = make_response(send_file(
                ruta_archivo,
                as_attachment=True,
                download_name=nombre_descarga, 
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ))
            
            #pegar  @after_this_request hasta response_redirect 
            # CONFIGURACIÓN CLAVE: Esta función se ejecuta DESPUÉS de enviar el archivo.
            # @after_this_request
            # def cleanup_and_redirect_to_success_js(response):
            #     # 1. Limpieza del archivo
            #     try:
            #         os.remove(ruta_archivo)
            #         print(f"Limpieza exitosa: {ruta_archivo} eliminado del servidor.")
            #     except OSError as e:
            #         print(f"Error en la limpieza del archivo de descarga (puede estar en uso): {e}")
                
            #     #FORZAR REDIRECCION CON PARAMETROS:
            #     #redirigimos al index con un indicador de exito y el nombre del archivo

            #     success_url = url_for('index', status ='success', file=nombre_descarga)
            #     response_redirect = redirect(success_url)
            #     return response_redirect

            # 2. Configuración para evitar caché y asegurar el cierre
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            
            # 3. La clave: usamos un bloque finally para asegurar la eliminación
            # DESPUÉS de que Flask haya preparado la respuesta.
            return response

        except Exception as e:
            print(f"Error al intentar enviar el archivo: {e}")
            return redirect(url_for('index'))
            
        # finally:

    return "Archivo no encontrado o ya fue descargado.", 404

if __name__ == '__main__':
    #configuracion para ejecutar Flask.
    print("* ejecutando flask. Asegúrate de tener las carpetas uploads, results y templates con pdf_toxls.html dentro.")
    app.run(debug=True)
