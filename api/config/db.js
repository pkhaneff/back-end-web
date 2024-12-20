import mongoose from "mongoose";

const connect = async () => {
    try {
        await mongoose.connect(process.env.MONGO)
        console.log('Connect Successfully!!!')
    } catch (error) {
        console.log('Connect failure!!!')
    }
}

export default {connect}