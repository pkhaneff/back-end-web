import jwt from 'jsonwebtoken'
import { errorHandler } from './error.js'

export const verifyToken = (req, res, next) => {
    const token = req.headers['authorization'] && req.headers['authorization'].split(' ')[1];  // 'Bearer <token>'
    if(!token){
        return next(errorHandler(401, 'khong co token'))
    }
    jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
        if(err){
            console.error('JWT verification error:', err);
            return next(errorHandler(401, 'Unauthorized'))
        } 
        req.user = 
        next()
    })
}