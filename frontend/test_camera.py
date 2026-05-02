import cv2
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from PIL import Image
import threading
import uvicorn

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_frame = None
frame_lock = threading.Lock()

@app.post('/frame')
async def receive_frame(request: Request):
    global latest_frame
    
    try:
        # Leer el contenido del body directamente
        contents = await request.body()
        img_data = Image.open(BytesIO(contents))
        frame_array = np.array(img_data)
        frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
        
        # lock ya que se accede desde los dos threads
        with frame_lock:
            latest_frame = frame_bgr
        
        return JSONResponse({'status': 'received'})
    
    except Exception as e:
        print(f'Error: {e}')
        return JSONResponse({'error': str(e)}, status_code=500)

def display_frames():
    """Muestra los frames"""
    while True:
        with frame_lock:
            frame = latest_frame
        
        if frame is not None:
            cv2.imshow('Mercadona', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()

def main():
    print('Servidor iniciado en http://127.0.0.1:5000')
    
    # Thread para mostrar frames
    display_thread = threading.Thread(target=display_frames, daemon=True)
    display_thread.start()
    
    # Ejecutar servidor
    uvicorn.run(app, host='0.0.0.0', port=5000, log_level='critical')

if __name__ == '__main__':
    main()





