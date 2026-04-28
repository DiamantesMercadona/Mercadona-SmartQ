from vision_engine import MSQEngine

def main():
    # Inicia el motor con la configuración predeterminada (webcam local)
    engine = MSQEngine(source=0)
    engine.process()

if __name__ == "__main__":
    main()