import axios, {AxiosInstance} from 'axios';
import {injectable} from 'inversify';
import type {HttpClient} from './HttpClient';

@injectable()
export class AxiosHttpClient implements HttpClient {
  private readonly client: AxiosInstance = axios.create();

  async get<T>(url: string): Promise<T> {
    const response = await this.client.get<T>(url);
    return response.data;
  }
}
