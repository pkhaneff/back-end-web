import express from 'express'
import dotenv from 'dotenv'
import route from './routes/index.route.js'
import db from './config/db.js'
import cookieParser from 'cookie-parser'
import cors from 'cors'

dotenv.config()

const app = express();

app.use(cors({
    origin: process.env.CLIENT_URL || '*',  
    credentials: true,                      
    methods: '*',                           
    allowedHeaders: '*',                
}))

app.use(express.json())
app.use(cookieParser())

route(app) 

db.connect()

app.listen(process.env.PORT, () => {
    console.log('Server is running !')
})

app.use(cors({
    origin: process.env.CLIENT_URL || '*',  
    credentials: true,                      
    methods: '*',                           
    allowedHeaders: '*',                
}))

app.use((err, req, res, next) => {
    const statusCode = err.statusCode || 500;
    const message = err.message || 'Internal Server Error'
    res.status(statusCode).json({
        success: false,
        statusCode,
        message
    })
})