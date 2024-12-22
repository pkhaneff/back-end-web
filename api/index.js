import express from 'express'
import dotenv from 'dotenv'
import route from './routes/index.route.js'
import db from './config/db.js'
import cookieParser from 'cookie-parser'
import cors from 'cors'

dotenv.config()

const app = express();

const corsOptions = {
    origin: 'http://localhost:5173', 
    credentials: true, 
    methods: ['GET', 'POST', 'PUT', 'DELETE'], 
    allowedHeaders: ['Content-Type', 'Authorization'], 
};

app.use(cors(corsOptions));

app.use(express.json());
app.use(cookieParser());

db.connect();

route(app);

app.use((err, req, res, next) => {
    const statusCode = err.statusCode || 500;
    const message = err.message || 'Internal Server Error';
    res.status(statusCode).json({
        success: false,
        statusCode,
        message,
    });
});

app.listen(process.env.PORT, () => {
    console.log('Server is running !');
});
