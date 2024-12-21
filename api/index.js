import express from 'express'
import dotenv from 'dotenv'
import route from './routes/index.route.js'
import db from './config/db.js'
import cookieParser from 'cookie-parser'
import cors from 'cors'

dotenv.config()

const app = express();

// Cấu hình CORS
const corsOptions = {
    origin: process.env.CLIENT_URL || 'http://localhost:5173',  // Đảm bảo rằng CLIENT_URL là URL frontend của bạn
    credentials: true,  // Cho phép gửi thông tin xác thực (cookie, JWT token)
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization'],
};

// Sử dụng middleware CORS
app.use(cors(corsOptions));

// Cấu hình OPTIONS để trả về các header CORS cho preflight request
app.options('*', cors(corsOptions)); 

app.use(express.json())
app.use(cookieParser())

db.connect()

route(app) 

app.use((err, req, res, next) => {
    const statusCode = err.statusCode || 500;
    const message = err.message || 'Internal Server Error'
    res.status(statusCode).json({
        success: false,
        statusCode,
        message
    })
})

app.listen(process.env.PORT, () => {
    console.log('Server is running !')
})